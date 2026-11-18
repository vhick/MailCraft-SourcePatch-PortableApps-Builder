        // Native MailCraft New Appointment / New Meeting form. Unlike b1r9's
        // separate form, this accepts the native fields and the selected
        // writable Google calendar. Only simple, timed events are supported.
        GooglePimEdit::NativeEvent {calendar,title,start,end,zone,location,description,required,optional,reminder,private,free} => {
            if title.trim().is_empty() || title.len() > 500 || calendar.is_empty() {
                return Err("Google event needs a title and a selected Google calendar".into());
            }
            let valid_local = |s: &str| -> bool {
                let b = s.as_bytes();
                b.len() == 16 && b[4]==b'-' && b[7]==b'-' && b[10]==b'T' && b[13]==b':' &&
                b.iter().enumerate().all(|(i,x)| matches!(i,4|7|10|13) || x.is_ascii_digit())
            };
            if !valid_local(start) || !valid_local(end) || end <= start {
                return Err("Google appointment needs valid start/end times (YYYY-MM-DDTHH:MM; end after start)".into());
            }
            if zone.trim().is_empty() || zone.len()>100 || zone.chars().any(|c| c == '\r' || c == '\n') {
                return Err("Select a supported time zone for the Google event".into());
            }
            if description.len()>10000 || location.len()>1000 {return Err("Google event description or location is too long".into());}
            let parse_guests = |input: &str, opt: bool| -> Result<Vec<Value>, String> {
                let mut out=Vec::new();
                for chunk in input.split(|c: char| c == ';' || c == ',').map(str::trim).filter(|s| !s.is_empty()) {
                    if chunk.len()>254 || chunk.chars().any(|c| matches!(c, '<' | '>' | '\r' | '\n' | ' ')) || !chunk.contains('@') || !chunk.split_once('@').is_some_and(|(a,b)| !a.is_empty() && b.contains('.')) {
                        return Err("For Google meetings, enter plain email addresses separated by semicolons (no display names)".into());
                    }
                    if out.len()>=50 {return Err("This pilot limits meeting invitations to 50 guests".into());}
                    out.push(serde_json::json!({"email":chunk,"optional":opt}));
                }
                Ok(out)
            };
            let mut attendees=parse_guests(required, false)?;
            attendees.extend(parse_guests(optional, true)?);
            let send = if attendees.is_empty() {"none"} else {"all"};
            let mut body=serde_json::json!({
                "summary":title,
                "start":{"dateTime":format!("{start}:00"),"timeZone":zone},
                "end":{"dateTime":format!("{end}:00"),"timeZone":zone},
                "description":description,"location":location,
                "visibility":if *private {"private"} else {"default"},
                "transparency":if *free {"transparent"} else {"opaque"},
                "reminders":if let Some(n)=reminder {serde_json::json!({"useDefault":false,"overrides":[{"method":"popup","minutes":(*n).min(40320)}]})} else {serde_json::json!({"useDefault":false})}
            });
            if !attendees.is_empty() { body["attendees"]=Value::Array(attendees); }
            ("POST",format!("https://www.googleapis.com/calendar/v3/calendars/{}/events?sendUpdates={send}",encode(calendar)),body,"")
        }
