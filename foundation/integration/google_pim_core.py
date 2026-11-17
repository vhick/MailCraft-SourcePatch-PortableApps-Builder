"""Read-only, account-scoped Google Calendar + People API sync foundation.

IMPORTANT: This is a tested integration core, NOT wired to MailCraft's GUI, account
lifecycle, Google OAuth or local mailbox. It does not read/write Google data by itself.
A host must supply an authenticated, timeout-bounded Google API transport and map
SyncCollection records to MailCraft native data model after successful unit tests.

No client id, client secret, refresh/access token, contact, or event is persisted.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import quote

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
CONTACTS_SCOPE = "https://www.googleapis.com/auth/contacts.readonly"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
PEOPLE_API = "https://people.googleapis.com/v1"
MAX_PAGES = 100

class ApiFailure(Exception):
    """Transport raised an HTTP failure. Never include response bodies with PII."""
    def __init__(self, status: int, code: str = ""):
        self.status = int(status)
        self.code = str(code)[:80]
        super().__init__(f"Google API HTTP {self.status}, {self.code or 'no details'}")

class InvalidApiData(Exception):
    pass


def safe_str(value: Any, limit: int = 2048) -> str:
    return value[:limit] if isinstance(value, str) else ""

@dataclass
class SyncCollection:
    """Changes for ONE Google account and ONE source collection.

    The consumer MUST apply changes atomically; `replace` clears only that
    account/collection and ONLY after an entire full sync succeeds.
    """
    account: str
    source: str
    collection: str
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    deleted: set[str] = field(default_factory=set)
    sync_token: str = ""
    replace: bool = False

    def key(self) -> tuple[str, str, str]:
        return (self.account, self.source, self.collection)


def account_key(address: str) -> str:
    address = address.strip().lower()
    if not address or '@' not in address or len(address) > 254 or any(ch in address for ch in '\r\n\x00'):
        raise ValueError('A primary Google email address is required')
    return address


def _array(value: Any) -> list[dict[str, Any]]:
    return [o for o in value if isinstance(o, dict)] if isinstance(value, list) else []


def _obj(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidApiData('Google API response is not an object')
    return value


def _field_array(src: dict, name: str, field: str = 'value', limit: int = 20) -> list[str]:
    return [v for item in _array(src.get(name))[:limit] if (v := safe_str(item.get(field), 512))]


def normalize_contact(raw: dict[str, Any]) -> tuple[str, dict[str, Any], bool]:
    key = safe_str(raw.get('resourceName'), 256)
    if not key.startswith('people/'):
        raise InvalidApiData('Contact missing valid resourceName')
    meta = _obj(raw.get('metadata', {}))
    if meta.get('deleted') is True:
        return key, {}, True
    names = _array(raw.get('names'))
    name = safe_str(names[0].get('displayName'), 256) if names else ''
    # Stable server identity; never use email address as unique contact key.
    return key, {
        'resource_id': key,
        'display_name': name,
        'emails': _field_array(raw, 'emailAddresses'),
        'phones': _field_array(raw, 'phoneNumbers'),
        'organization': _field_array(raw, 'organizations', 'name')[:1],
        'etag': safe_str(raw.get('etag'), 256),
    }, False


def normalize_event(raw: dict[str, Any]) -> tuple[str, dict[str, Any], bool]:
    key = safe_str(raw.get('id'), 512)
    if not key or '/' in key or '\x00' in key:
        raise InvalidApiData('Event missing valid id')
    if raw.get('status') == 'cancelled':
        return key, {}, True
    start = _obj(raw.get('start', {}))
    end = _obj(raw.get('end', {}))
    # Retain native Google format. MailCraft adapter must perform verified TZ
    # conversion to preserve all-day events, recurrence, and daylight-saving time.
    return key, {
        'event_id': key,
        'summary': safe_str(raw.get('summary'), 512),
        'description': safe_str(raw.get('description'), 8192),
        'start_date_time': safe_str(start.get('dateTime'), 128),
        'end_date_time': safe_str(end.get('dateTime'), 128),
        'start_date': safe_str(start.get('date'), 16),
        'end_date': safe_str(end.get('date'), 16),
        'start_timezone': safe_str(start.get('timeZone'), 128),
        'end_timezone': safe_str(end.get('timeZone'), 128),
        'recurrence': [safe_str(x, 1024) for x in raw.get('recurrence', [])[:50]] if isinstance(raw.get('recurrence'), list) else [],
        'recurring_event_id': safe_str(raw.get('recurringEventId'), 512),
        'etag': safe_str(raw.get('etag'), 256),
        'visibility': safe_str(raw.get('visibility'), 64),
    }, False


# Transport accepts (url, query_params) and returns parsed JSON. A future
# MailCraft host adapter must add Bearer auth, TLS, response size/time limits.
Transport = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


def _sync_pages(
    *, account: str, source: str, collection: str, url: str,
    base_params: dict[str, str], old_token: str,
    items_field: str, normalize: Callable[[dict[str, Any]], tuple[str, dict[str, Any], bool]],
    fetch: Transport
) -> SyncCollection:
    """Bounded page traversal and safe single-retry fallback for expired tokens.

    Fail closed on malformed final pages, duplicates, and unbounded pagination.
    No partial result is ever returned on a failed refresh.
    """
    for attempt in range(2):
        incremental = bool(old_token) and attempt == 0
        params = dict(base_params)
        if incremental:
            params['syncToken'] = old_token
        elif source == 'contacts':
            params['requestSyncToken'] = 'true'
        result = SyncCollection(account, source, collection, replace=not incremental)
        visited: set[str] = set()
        try:
            for page in range(MAX_PAGES):
                payload = _obj(dict(fetch(url, params)))
                for item in _array(payload.get(items_field)):
                    key, normalized, deleted = normalize(item)
                    if deleted:
                        result.deleted.add(key)
                        result.items.pop(key, None)
                    else:
                        result.items[key] = normalized
                        result.deleted.discard(key)
                cursor = safe_str(payload.get('nextPageToken'), 2048)
                if cursor:
                    if cursor in visited:
                        raise InvalidApiData('Repeated Google API page token')
                    visited.add(cursor)
                    params['pageToken'] = cursor
                    continue
                token = safe_str(payload.get('nextSyncToken'), 2048)
                if not token:
                    raise InvalidApiData('Final page did not provide nextSyncToken')
                result.sync_token = token
                return result
            raise InvalidApiData('Google API exceeded maximum number of pages')
        except ApiFailure as exc:
            expired_calendar = source == 'calendar' and exc.status == 410
            expired_contacts = source == 'contacts' and (exc.code == 'EXPIRED_SYNC_TOKEN' or exc.status == 410)
            if incremental and (expired_calendar or expired_contacts):
                # Drop syncToken, get a complete snapshot; no stale incremental merge.
                continue
            raise
    raise InvalidApiData('Google incremental sync could not recover')


def list_calendars(fetch: Transport) -> list[dict[str, str]]:
    # Explicit calendar list is required to support multiple calendars.
    url = f'{CALENDAR_API}/users/me/calendarList'
    params: dict[str, str] = {'maxResults': '250'}
    seen: set[str] = set()
    calendars: dict[str, dict[str, str]] = {}
    for _ in range(MAX_PAGES):
        data = _obj(dict(fetch(url, params)))
        for raw in _array(data.get('items')):
            cid = safe_str(raw.get('id'), 512)
            if cid:
                calendars[cid] = {
                    'id': cid,
                    'name': safe_str(raw.get('summary'), 256),
                    'timezone': safe_str(raw.get('timeZone'), 128),
                    'access_role': safe_str(raw.get('accessRole'), 64),
                }
        cursor = safe_str(data.get('nextPageToken'), 2048)
        if not cursor:
            return list(calendars.values())
        if cursor in seen:
            raise InvalidApiData('Repeated calendarList page token')
        seen.add(cursor)
        params['pageToken'] = cursor
    raise InvalidApiData('calendarList exceeded maximum number of pages')


def sync_events(account: str, calendar_id: str, token: str, fetch: Transport) -> SyncCollection:
    account = account_key(account)
    if not calendar_id or len(calendar_id) > 512:
        raise ValueError('Missing calendar id')
    url = f'{CALENDAR_API}/calendars/{quote(calendar_id, safe="")}/events'
    return _sync_pages(
        account=account, source='calendar', collection=calendar_id, url=url,
        base_params={'maxResults': '2500', 'showDeleted': 'true', 'singleEvents': 'false'},
        old_token=token, items_field='items', normalize=normalize_event, fetch=fetch
    )


def sync_contacts(account: str, token: str, fetch: Transport) -> SyncCollection:
    account = account_key(account)
    return _sync_pages(
        account=account, source='contacts', collection='personal',
        url=f'{PEOPLE_API}/people/me/connections',
        base_params={'pageSize': '1000', 'personFields': 'names,emailAddresses,phoneNumbers,organizations,metadata'},
        old_token=token, items_field='connections', normalize=normalize_contact, fetch=fetch
    )


def apply_change(current: Mapping[str, dict[str, Any]], change: SyncCollection) -> dict[str, dict[str, Any]]:
    """Return new state, never mutate the caller. The host owns storage transaction."""
    out = {} if change.replace else dict(current)
    for key in change.deleted:
        out.pop(key, None)
    out.update(change.items)
    return out
