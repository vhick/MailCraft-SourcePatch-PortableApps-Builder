#!/usr/bin/env python3
"""Experimental b1r6 native Google Calendar/Contacts integration for exact MailCraft v0.13.0.

Fail closed on any missing upstream anchor. Patch only official source at the
builder-selected immutable release commit. Never copy tokens/credentials.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(body: str, old: str, new: str, name: str) -> str:
    n = body.count(old)
    if n != 1:
        raise RuntimeError(f"b1r6 upstream source drift: {name} expected once, found {n}. Stop and inspect; do not force the patch.")
    return body.replace(old, new, 1)


def plan(src: Path) -> dict[Path, str]:
    oauth = src/'crates/net/src/oauth.rs'
    net_lib = src/'crates/net/src/lib.rs'
    ui_lib = src/'crates/ui-egui/src/lib.rs'
    main = src/'apps/mailcraft/src/main.rs'
    net_mod = src/'crates/net/src/google_pim.rs'
    ui_mod = src/'crates/ui-egui/src/google_pim.rs'
    files = [oauth, net_lib, ui_lib, main]
    if any(not f.is_file() for f in files):
        raise RuntimeError('b1r6 missing upstream source file(s)')
    if net_mod.exists() or ui_mod.exists():
        raise RuntimeError('b1r6 upstream already defines Google PIM modules; do not overwrite')
    a, b, c, d = (f.read_text(encoding='utf-8') for f in files)
    a = replace_once(a,
        'const GOOGLE_SCOPE: &str = "https://mail.google.com/ openid email";',
        'const GOOGLE_SCOPE: &str = "https://mail.google.com/ openid email";\n'
        '/// Additional optional read-only permissions requested at Google sign-in.\n'
        'const GOOGLE_PIM_SCOPE: &str = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/contacts.readonly";',
        'Google scope constants')
    a = replace_once(a,
        'scope: GOOGLE_SCOPE.into(),\n                consent: String::new(),',
        'scope: format!("{GOOGLE_SCOPE} {GOOGLE_PIM_SCOPE}"),\n                consent: String::new(),',
        'Google sign-in combined scopes')
    a = replace_once(a,
        'pub fn refresh(oauth: &OAuth, refresh_token: &str) -> Result<Tokens, NetError> {\n    refresh_for(oauth, refresh_token, Resource::Mail)\n}',
        'pub fn refresh(oauth: &OAuth, refresh_token: &str) -> Result<Tokens, NetError> {\n'
        '    refresh_for(oauth, refresh_token, Resource::Mail)\n'
        '}\n'
        '/// Refresh Calendar and Contacts access separately: a failure cannot break IMAP mail.\n'
        'pub fn refresh_google_pim(oauth: &OAuth, refresh_token: &str) -> Result<Tokens, NetError> {\n'
        '    if oauth.provider != OAuthProvider::Google {\n'
        '        return Err(NetError::Config("Google PIM requires Google OAuth".into()));\n'
        '    }\n'
        '    let mut ep = Endpoints::of(oauth);\n'
        '    ep.scope = format!("{GOOGLE_SCOPE} {GOOGLE_PIM_SCOPE}");\n'
        '    ep.consent.clear();\n'
        '    refresh_google_at(&ep, oauth, GOOGLE_DESKTOP_SECRET, refresh_token)\n'
        '}',
        'PIM refresh function')
    b = replace_once(b,
        '#[cfg(not(target_arch = "wasm32"))]\npub mod graph;',
        '#[cfg(not(target_arch = "wasm32"))]\npub mod graph;\n#[cfg(not(target_arch = "wasm32"))]\npub mod google_pim;',
        'net module registration')
    c = replace_once(c, 'mod calendar_sync;\n', 'mod calendar_sync;\npub mod google_pim;\n', 'UI module registration')
    c = replace_once(c,
        'pub graph: Option<Box<dyn Fn(GraphRequest) -> Receiver<GraphResult>>>,',
        'pub graph: Option<Box<dyn Fn(GraphRequest) -> Receiver<GraphResult>>>,\n'
        '    /// Desktop: optional read-only Google Calendar/Contacts jobs, separate from Gmail.\n'
        '    pub google_pim: Option<Box<dyn Fn(google_pim::GooglePimRequest) -> Receiver<google_pim::GooglePimResult>>>,',
        'Services Google connector')
    c = replace_once(c,
        '    calendar: calendar_sync::CalendarSync,',
        '    calendar: calendar_sync::CalendarSync,\n'
        '    google_pim: google_pim::GooglePimSync,',
        'MailApp Google state')
    c = replace_once(c,
        '            calendar: Default::default(),',
        '            calendar: Default::default(),\n'
        '            google_pim: Default::default(),',
        'MailApp Google initializer')
    c = replace_once(c, '        self.poll_calendar();', '        self.poll_calendar();\n        self.poll_google_pim();', 'poll native Google results')
    c = replace_once(c, '            self.calendar_tick(ctx);', '            self.calendar_tick(ctx);\n            self.google_pim_tick(ctx);', 'start native Google jobs')
    d = replace_once(d, '    let search_ctx = ctx.clone();', '    let search_ctx = ctx.clone();\n    let google_pim_ctx = ctx.clone();', 'host Google context')
    d = replace_once(d,
        '        graph: Some(Box::new({\n            let host = host.clone();\n            move |request: GraphRequest| host_job(host.as_ref(), &graph_ctx, "microsoft graph", move || mailcraft_host::graph::graph(request))\n        })),',
        '        graph: Some(Box::new({\n'
        '            let host = host.clone();\n'
        '            move |request: GraphRequest| host_job(host.as_ref(), &graph_ctx, "microsoft graph", move || mailcraft_host::graph::graph(request))\n'
        '        })),\n'
        '        google_pim: Some(Box::new(move |request: mailcraft_ui_egui::google_pim::GooglePimRequest| {\n'
        '            background(&google_pim_ctx, "google calendar and contacts", move || {\n'
        '                let account = request.account;\n'
        '                let mut response = mailcraft_ui_egui::google_pim::GooglePimResult {\n'
        '                    account: account.id, email: account.email.clone(), ..Default::default()\n'
        '                };\n'
        '                match mailcraft_net::oauth::refresh_google_pim(&request.oauth, &request.refresh) {\n'
        '                    Ok(tokens) => {\n'
        '                        let data = mailcraft_net::google_pim::download(&account, &tokens.access);\n'
        '                        response.contacts = data.contacts;\n'
        '                        response.calendars = data.calendars;\n'
        '                        response.events = data.events;\n'
        '                        response.errors = data.errors;\n'
        '                        response.refreshed = Some(tokens);\n'
        '                    }\n'
        '                    Err(_) => response.errors.push("New Google Calendar/Contacts consent is required: reconnect Google".into()),\n'
        '                }\n'
        '                response\n'
        '            })\n'
        '        })),',
        'host Google run hook')
    return {
        oauth: a, net_lib: b, ui_lib: c, main: d,
        net_mod: (ROOT/'patches/google_pim_net.rs').read_text(encoding='utf-8'),
        ui_mod: (ROOT/'patches/google_pim_ui.rs').read_text(encoding='utf-8'),
    }


def patch(src: Path) -> None:
    update = plan(src)  # Validate every anchor before changing anything.
    for path, source in update.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8', newline='\n')
    print('b1r6: Google Calendar + Contacts read-only native connector patch applied')

if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('--source', required=True, type=Path)
    opts = cli.parse_args()
    patch(opts.source)
