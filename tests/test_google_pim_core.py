import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integration'))
from google_pim_core import (
    ApiFailure, InvalidApiData, account_key, apply_change, list_calendars,
    sync_contacts, sync_events, normalize_event, normalize_contact,
)

class PimTests(unittest.TestCase):
    def test_calendar_multi_page_incremental_and_tombstone(self):
        calls=[]
        def fake(url,p):
            calls.append(dict(p))
            if 'pageToken' not in p:
                return {'items':[{'id':'new','summary':'Meeting','start':{'dateTime':'2026-11-18T10:00:00+08:00'},'end':{'dateTime':'2026-11-18T11:00:00+08:00'}}, {'id':'old','status':'cancelled'}], 'nextPageToken':'more'}
            return {'items':[{'id':'again','summary':'Another','start':{'date':'2026-11-19'},'end':{'date':'2026-11-20'}}], 'nextSyncToken':'final'}
        c=sync_events(' A@Example.com ', 'a@example.com', 'previous', fake)
        self.assertEqual(c.account,'a@example.com'); self.assertFalse(c.replace)
        self.assertEqual(c.deleted,{'old'}); self.assertEqual(set(c.items),{'new','again'})
        self.assertEqual(c.sync_token,'final')
        self.assertEqual(calls[0]['syncToken'],'previous')
        self.assertEqual(calls[1]['pageToken'],'more')
        self.assertEqual(apply_change({'old':{'x':1},'leave':{'x':2}},c)['leave'], {'x':2})
    def test_calendar_expired_token_rolls_back_and_full_rebuild(self):
        counter=[0]
        def fake(_,p):
            counter[0]+=1
            if 'syncToken' in p: raise ApiFailure(410)
            return {'items':[{'id':'fresh','summary':'new'}], 'nextSyncToken':'reset'}
        c=sync_events('a@b.com','primary','expired',fake)
        self.assertTrue(c.replace); self.assertEqual(c.sync_token,'reset')
        self.assertEqual(set(apply_change({'stale':{}},c)),{'fresh'})
        self.assertEqual(counter[0],2)
    def test_contacts_expired_token(self):
        def fake(_,p):
            if 'syncToken' in p: raise ApiFailure(400, 'EXPIRED_SYNC_TOKEN')
            return {'connections':[{'resourceName':'people/1','names':[{'displayName':'Test'}]}], 'nextSyncToken':'v2'}
        c=sync_contacts('u@w.com','expired',fake)
        self.assertTrue(c.replace); self.assertEqual(c.items['people/1']['display_name'],'Test')
    def test_contacts_empty_and_email_stability(self):
        c=sync_contacts('u@w.com','',lambda u,p:{'connections':[{'resourceName':'people/1','emailAddresses':[{'value':'x@y.com'}]},{'resourceName':'people/2','emailAddresses':[{'value':'x@y.com'}]}],'nextSyncToken':'s'})
        self.assertEqual(len(c.items),2)
    def test_person_deletion_tombstone(self):
        c=sync_contacts('a@b.com','s',lambda u,p:{'connections':[{'resourceName':'people/old','metadata':{'deleted':True}}],'nextSyncToken':'new'})
        self.assertIn('people/old',c.deleted)
    def test_missing_token_fail_closed(self):
        with self.assertRaises(InvalidApiData): sync_events('a@b.com','p','',lambda u,p:{'items':[]})
    def test_api_failure_no_state_change(self):
        before={'existing':{'x':1}}
        with self.assertRaises(ApiFailure): sync_contacts('a@b.com','',lambda u,p:(_ for _ in ()).throw(ApiFailure(429)))
        self.assertEqual(before,{'existing':{'x':1}})
    def test_loop_page_token_detected(self):
        with self.assertRaises(InvalidApiData): sync_contacts('a@b.com','',lambda u,p:{'connections':[],'nextPageToken':'loop'})
    def test_calendar_listing(self):
        out=list_calendars(lambda u,p:{'items':[{'id':'a','summary':'Work','timeZone':'Asia/Manila'}]})
        self.assertEqual(out[0]['name'],'Work')
    def test_source_account_isolation(self):
        c1=sync_contacts('a@b.com','',lambda u,p:{'connections':[],'nextSyncToken':'T'})
        c2=sync_contacts('c@b.com','',lambda u,p:{'connections':[],'nextSyncToken':'T'})
        self.assertNotEqual(c1.key(),c2.key())
    def test_all_day_preserved(self):
        k,e,deleted=normalize_event({'id':'x','start':{'date':'2026-11-20'},'end':{'date':'2026-11-21'}})
        self.assertEqual(e['start_date'],'2026-11-20'); self.assertFalse(deleted)
    def test_unknown_contact_id_refused(self):
        with self.assertRaises(InvalidApiData): normalize_contact({'names':[{'displayName':'Oops'}]})
    def test_no_external_calls_without_transport(self):
        # API client intentionally has no built-in network access or OAuth secrets.
        self.assertEqual(account_key(' u@example.com '),'u@example.com')

if __name__=='__main__': unittest.main()
