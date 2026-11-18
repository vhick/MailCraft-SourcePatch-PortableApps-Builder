#!/usr/bin/env python3
"""b1r11: exact-source compatibility repair after b1r10 native forms patch.

Repair v0.13.0 Google pilot's all-day event creation, without touching upstream
native delete/edit routes or replacing Google API permission checks.
"""
from pathlib import Path
import argparse


def exactly_once(content, old, new, what):
    found = content.count(old)
    if found != 1:
        raise RuntimeError(f'b1r11 {what}: expected one anchor, found {found}; STOP, no files changed')
    return content.replace(old, new, 1)


def plan(source: Path):
    model = source / 'crates/model/src/remote.rs'
    net = source / 'crates/net/src/google_pim.rs'
    ui = source / 'crates/ui-egui/src/google_pim.rs'
    if not all(p.is_file() for p in (model, net, ui)):
        raise RuntimeError('b1r11 requires b1r10 native Google forms to have been applied')
    a, b, c = (p.read_text(encoding='utf-8') for p in (model, net, ui))

    a = exactly_once(a,
        'NativeEvent { calendar: String, title: String, start: String, end: String,\n        zone: String,',
        'NativeEvent { calendar: String, title: String, start: String, end: String,\n        all_day: bool, zone: String,',
        'all-day native event model')

    c = exactly_once(c,
        '        if params.get("allDay").and_then(Value::as_bool) == Some(true) {\n            return Some(Err("All-day Google events are not included in this native-form pilot. Use Google Calendar web.".into()));\n        }\n',
        '',
        'remove obsolete all-day refusal')
    c = exactly_once(c,
        'calendar: remote_calendar, title: name("title"), start: name("start"), end: name("end"), zone,',
        'calendar: remote_calendar, title: name("title"), start: name("start"), end: name("end"),\n            all_day: params.get("allDay").and_then(Value::as_bool) == Some(true), zone,',
        'route all-day flag')

    b = exactly_once(b,
        'GooglePimEdit::NativeEvent {calendar,title,start,end,zone,location,description,required,optional,reminder,private,free} => {',
        'GooglePimEdit::NativeEvent {calendar,title,start,end,all_day,zone,location,description,required,optional,reminder,private,free} => {',
        'native event network arm')
    b = exactly_once(b,
        '''            if !valid_local(start) || !valid_local(end) || end <= start {
                return Err("Google appointment needs valid start/end times (YYYY-MM-DDTHH:MM; end after start)".into());
            }
''',
        '''            // The MailCraft all-day form uses inclusive last day. Google Calendar
            // requires an EXCLUSIVE end date: convert 20 Nov -> 21 Nov before POST.
            let (start_json, end_json) = if *all_day {
                let start_day = mailcraft_time::Date::parse_iso(start)
                    .ok_or_else(|| "Google all-day event needs a valid start date".to_string())?;
                let end_day = mailcraft_time::Date::parse_iso(end)
                    .ok_or_else(|| "Google all-day event needs a valid end date".to_string())?;
                if end_day < start_day {
                    return Err("All-day Google event must end on or after its start day".into());
                }
                (serde_json::json!({"date":start_day.iso()}),
                 serde_json::json!({"date":end_day.add_days(1).iso()}))
            } else {
                if !valid_local(start) || !valid_local(end) || end <= start {
                    return Err("Google appointment needs valid start/end times (YYYY-MM-DDTHH:MM; end after start)".into());
                }
                (serde_json::json!({"dateTime":format!("{start}:00"),"timeZone":zone}),
                 serde_json::json!({"dateTime":format!("{end}:00"),"timeZone":zone}))
            };
''',
        'all-day exclusive end conversion')
    b = exactly_once(b,
        '''                "start":{"dateTime":format!("{start}:00"),"timeZone":zone},
                "end":{"dateTime":format!("{end}:00"),"timeZone":zone},''',
        '''                "start": start_json,
                "end": end_json,''',
        'use validated event times')

    return {model:a, net:b, ui:c}


def patch(source:Path):
    changes = plan(source)
    for file, content in changes.items():
        file.write_text(content, encoding='utf-8')
    print('b1r11 all-day fix applied, Google event Delete remains intentionally disabled')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source', required=True, type=Path)
    patch(p.parse_args().source)
