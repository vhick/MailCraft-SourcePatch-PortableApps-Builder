        let department=first_str(&item,"organizations","department");
        let notes=first_str(&item,"biographies","value");
        let websites=item.get("urls").and_then(Value::as_array).map(|xs|
            xs.iter().filter_map(|row|row.get("value").and_then(Value::as_str).map(str::to_owned)).take(50).collect()
        ).unwrap_or_default();
        let addresses=item.get("addresses").and_then(Value::as_array).map(|xs|
            xs.iter().map(|row|mailcraft_model::PostalAddress {
                label:txt(row,"type").to_owned(), street:txt(row,"streetAddress").to_owned(),
                city:txt(row,"city").to_owned(), region:txt(row,"region").to_owned(),
                postal_code:txt(row,"postalCode").to_owned(), country:txt(row,"country").to_owned(),
            }).take(50).collect()
        ).unwrap_or_default();
        let birthday=item.get("birthdays").and_then(Value::as_array).and_then(|a|a.first())
            .and_then(|row|row.get("date"))
            .and_then(|date|{
                let (y,m,d)=(date.get("year")?.as_u64()?,date.get("month")?.as_u64()?,date.get("day")?.as_u64()?);
                mailcraft_time::Date::parse_iso(&format!("{y:04}-{m:02}-{d:02}"))
            });
