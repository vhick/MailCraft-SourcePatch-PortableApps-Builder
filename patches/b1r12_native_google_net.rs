        GooglePimEdit::NativeUpdateEvent {calendar,event,etag,fields,zone} => {
            if calendar.is_empty() || event.is_empty() || etag.is_empty() || zone.is_empty() {
                return Err("Google event ID, version and time zone are required".into());
            }
            let data:Value=serde_json::from_str(fields).map_err(|_|"Invalid native event changes")?;
            let changes=data.as_object().ok_or("Invalid event changes")?;
            let allowed=["id","scope","occurrence","title","location","description","start","end","allDay","startZone","endZone","reminder","showAs","private"];
            if changes.keys().any(|k|!allowed.contains(&k.as_str())) {return Err("Unsafe native event edit field".into());}
            let mut body=serde_json::Map::new();
            for (key,out) in [("title","summary"),("location","location"),("description","description")] {
                if let Some(v)=changes.get(key) {body.insert(out.into(),v.clone());}
            }
            if let Some(v)=changes.get("private").and_then(Value::as_bool) {
                body.insert("visibility".into(),serde_json::json!(if v {"private"} else {"default"}));
            }
            if let Some(v)=changes.get("showAs").and_then(Value::as_str) {
                if v!="free" && v!="busy" {return Err("Only Free/Busy can be set on Google events".into());}
                body.insert("transparency".into(),serde_json::json!(if v=="free" {"transparent"} else {"opaque"}));
            }
            if changes.contains_key("reminder") {
                let value=changes.get("reminder").and_then(Value::as_u64);
                if value.is_some_and(|n|n>40320){return Err("Reminder cannot exceed four weeks".into());}
                body.insert("reminders".into(),value.map_or(serde_json::json!({"useDefault":false}),|n|serde_json::json!({"useDefault":false,"overrides":[{"method":"popup","minutes":n}]})));
            }
            if changes.contains_key("start") || changes.contains_key("end") || changes.contains_key("allDay") {
                let start=changes.get("start").and_then(Value::as_str).ok_or("Event start missing")?;
                let end=changes.get("end").and_then(Value::as_str).ok_or("Event end missing")?;
                let all_day=changes.get("allDay").and_then(Value::as_bool).unwrap_or(false);
                let start_zone=changes.get("startZone").and_then(Value::as_str).filter(|s|!s.is_empty()).unwrap_or(zone);
                let end_zone=changes.get("endZone").and_then(Value::as_str).filter(|s|!s.is_empty()).unwrap_or(start_zone);
                if start_zone!=end_zone {return Err("Cross-time-zone edits need Google Calendar web".into());}
                if all_day {
                    let s=mailcraft_time::Date::parse_iso(start).ok_or("Invalid all-day start")?;
                    let e=mailcraft_time::Date::parse_iso(end).ok_or("Invalid all-day end")?;
                    if e<s {return Err("All-day end must be on or after start".into());}
                    body.insert("start".into(),serde_json::json!({"date":s.iso()}));
                    body.insert("end".into(),serde_json::json!({"date":e.add_days(1).iso()}));
                } else {
                    let valid=|stamp:&str| stamp.len()==16 && stamp.chars().nth(10)==Some('T');
                    if !valid(start) || !valid(end) || end<=start {return Err("Invalid event start or end time".into());}
                    body.insert("start".into(),serde_json::json!({"dateTime":format!("{start}:00"),"timeZone":start_zone}));
                    body.insert("end".into(),serde_json::json!({"dateTime":format!("{end}:00"),"timeZone":start_zone}));
                }
            }
            if body.is_empty() {return Err("No supported event changes to save".into());}
            ("PATCH",format!("https://www.googleapis.com/calendar/v3/calendars/{}/events/{}?sendUpdates=none",encode(calendar),encode(event)),Value::Object(body),etag.as_str())
        }
        GooglePimEdit::NativeDeleteEvent {calendar,event,etag} => {
            if calendar.is_empty() || event.is_empty() || etag.is_empty() || calendar.len()>1024 || event.len()>1024 {
                return Err("Google event cannot be deleted without a valid saved ID/version".into());
            }
            ("DELETE",format!("https://www.googleapis.com/calendar/v3/calendars/{}/events/{}?sendUpdates=none",encode(calendar),encode(event)),Value::Null,etag.as_str())
        }
        GooglePimEdit::NativeContact {resource,etag,fields} => {
            let source:Value=serde_json::from_str(fields).map_err(|_|"Invalid native contact form")?;
            let source=source.as_object().ok_or("Expected contact form object")?;
            let allowed=["id","first","last","company","title","department","emails","phones","address","website","notes","birthday"];
            if source.keys().any(|k|!allowed.contains(&k.as_str())) {return Err("Unsafe contact field was refused".into());}
            let creating=resource.is_empty();
            if !creating && (!resource.starts_with("people/") || resource.len()<=7 || etag.is_empty() ||
                !resource[7..].bytes().all(|b|b.is_ascii_alphanumeric() || matches!(b,b'-'|b'_'))) {
                return Err("Cannot edit contact without Google resource and ETag".into());
            }
            let mut person=serde_json::Map::new();
            let mut mask=Vec::<&str>::new();
            let txt=|key:&str| source.get(key).and_then(Value::as_str).unwrap_or("").trim().to_owned();
            if source.contains_key("first") || source.contains_key("last") {
                let (first,last)=(txt("first"),txt("last"));
                if first.len()>200 || last.len()>200 {return Err("Contact name is too long".into());}
                person.insert("names".into(),if first.is_empty() && last.is_empty() {serde_json::json!([])} else {serde_json::json!([{"givenName":first,"familyName":last}])});
                mask.push("names");
            }
            if source.contains_key("company") || source.contains_key("title") || source.contains_key("department") {
                let (company,title,department)=(txt("company"),txt("title"),txt("department"));
                if company.len()>500 || title.len()>500 || department.len()>500 {return Err("Organization field too long".into());}
                person.insert("organizations".into(),if company.is_empty() && title.is_empty() && department.is_empty() {serde_json::json!([])}
                    else {serde_json::json!([{"name":company,"title":title,"department":department}])});
                mask.push("organizations");
            }
            for (input,output,kind) in [("emails","emailAddresses","email"),("phones","phoneNumbers","phone")] {
                if let Some(rows)=source.get(input) {
                    let rows=rows.as_array().ok_or("Contact rows must be a list")?;
                    if rows.len()>20 {return Err("Too many contact addresses or phones".into());}
                    let mut out=Vec::<Value>::new();
                    for row in rows {
                        let value=row.get("value").and_then(Value::as_str).unwrap_or("").trim();
                        if value.is_empty() {continue;}
                        if value.len()>254 || value.contains('\n') || value.contains('\r') {return Err("Invalid contact email or phone".into());}
                        if kind=="email" && (!value.contains('@') || value.contains(' ')) {return Err("Invalid contact email".into());}
                        let label=row.get("label").and_then(Value::as_str).unwrap_or("other");
                        out.push(serde_json::json!({"value":value,"type":label}));
                    }
                    person.insert(output.into(),Value::Array(out));mask.push(output);
                }
            }
            if let Some(address)=source.get("address") {
                let get=|k:&str| address.get(k).and_then(Value::as_str).unwrap_or("").trim().to_owned();
                let (street,city,region,postal,country)=(get("street"),get("city"),get("region"),get("postalCode"),get("country"));
                if [street.as_str(),city.as_str(),region.as_str(),postal.as_str(),country.as_str()].iter().any(|x|x.len()>1000) {
                    return Err("Address field too long".into());
                }
                let val=if [street.as_str(),city.as_str(),region.as_str(),postal.as_str(),country.as_str()].iter().all(|x|x.is_empty()) {
                    serde_json::json!([])
                } else {serde_json::json!([{"streetAddress":street,"city":city,"region":region,"postalCode":postal,"country":country,
                    "type":get("label")}])};
                person.insert("addresses".into(),val);mask.push("addresses");
            }
            if source.contains_key("website") {
                let url=txt("website");if url.len()>2000 || (!url.is_empty() && !url.starts_with("https://") && !url.starts_with("http://")) {
                    return Err("Website must start with https:// or http://".into());
                }
                person.insert("urls".into(),if url.is_empty(){serde_json::json!([])} else {serde_json::json!([{"value":url}])});mask.push("urls");
            }
            if source.contains_key("notes") {
                let notes=txt("notes");if notes.len()>10000 {return Err("Contact notes too long".into());}
                person.insert("biographies".into(),if notes.is_empty(){serde_json::json!([])} else {serde_json::json!([{"value":notes,"contentType":"TEXT_PLAIN"}])});mask.push("biographies");
            }
            if source.contains_key("birthday") {
                let value=source.get("birthday").and_then(Value::as_str).unwrap_or("");
                if value.is_empty() || source.get("birthday").is_some_and(Value::is_null) {
                    person.insert("birthdays".into(),serde_json::json!([]));
                } else {
                    let date=mailcraft_time::Date::parse_iso(value).ok_or("Birthday must be YYYY-MM-DD")?;
                    let iso=date.iso();let parts:Vec<&str>=iso.split('-').collect();
                    let (year,month,day)=(parts[0].parse::<u32>().map_err(|_|"Invalid birthday year")?,
                        parts[1].parse::<u32>().map_err(|_|"Invalid birthday month")?,parts[2].parse::<u32>().map_err(|_|"Invalid birthday day")?);
                    person.insert("birthdays".into(),serde_json::json!([{"date":{"year":year,"month":month,"day":day}}]));
                }
                mask.push("birthdays");
            }
            if mask.is_empty(){return Err("No supported contact fields to save".into());}
            let body=Value::Object(person);
            if creating {
                ("POST","https://people.googleapis.com/v1/people:createContact?personFields=names,emailAddresses,metadata".into(),body,"")
            } else {
                let mut obj=body.as_object().cloned().ok_or("Contact object missing")?;
                obj.insert("resourceName".into(),serde_json::json!(resource));
                obj.insert("metadata".into(),serde_json::json!({"sources":[{"type":"CONTACT","etag":etag}]}));
                ("PATCH",format!("https://people.googleapis.com/v1/{}:updateContact?updatePersonFields={}&personFields=names,emailAddresses,metadata",resource,mask.join(",")),Value::Object(obj),"")
            }
        }
        GooglePimEdit::NativeDeleteContact {resource,etag} => {
            if !resource.starts_with("people/") || resource.len()<=7 || etag.is_empty() ||
                !resource[7..].bytes().all(|b|b.is_ascii_alphanumeric() || matches!(b,b'-'|b'_')) {
                return Err("Contact deletion needs a verified Google resource and version".into());
            }
            // People deletion has no ETag request argument. Verify the saved
            // version immediately before DELETE instead of silently deleting a
            // contact that another device changed since our last sync.
            let url=format!("https://people.googleapis.com/v1/{}?personFields=metadata",resource);
            let bearer=format!("Bearer {access}");
            let auth=[("Authorization",bearer.as_str()),("Accept","application/json")];
            let check=https::send(&Request{method:"GET",url:&url,fields:&auth,body:&[],max_response:100000,trusted:""})
                .map_err(|_|"Could not verify current contact version; deletion cancelled".to_string())?;
            if check.status!=200 {return Err(format!("Google contact version check returned HTTP {}; deletion cancelled",check.status));}
            let person:Value=serde_json::from_slice(&check.body).map_err(|_|"Cannot read contact version; deletion cancelled")?;
            let current=person.pointer("/metadata/sources").and_then(Value::as_array)
                .and_then(|sources|sources.iter().find(|s|s.get("type").and_then(Value::as_str)==Some("CONTACT")))
                .and_then(|s|s.get("etag")).and_then(Value::as_str).unwrap_or("");
            if current!=etag {return Err("Google contact has changed since sync. Refresh it before deleting; nothing was removed".into());}
            ("DELETE",format!("https://people.googleapis.com/v1/{}:deleteContact",resource),Value::Null,"")
        }
