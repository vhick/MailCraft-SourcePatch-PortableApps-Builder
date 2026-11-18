                // b1r9: writes happen only after a user presses Save in the Google editor.
                // Never auto-repeat a POST/PATCH after an ambiguous network failure.
                if let Some(edit) = request.edit.as_ref() {
                    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
                        .map(|d| d.as_secs() as i64).unwrap_or(i64::MAX);
                    let mut valid_access = request.access.clone();
                    if valid_access.is_empty() || request.expires_at <= now.saturating_add(90) {
                        match mailcraft_net::oauth::refresh_google_pim(&request.oauth, &request.refresh) {
                            Ok(tokens) => { valid_access = tokens.access.clone(); response.refreshed = Some(tokens); },
                            Err(_) => { response.errors.push("Google write token refresh failed; reconnect before editing".into()); return response; }
                        }
                    }
                    match mailcraft_net::google_pim::write(&valid_access, edit) {
                        Ok(()) => {
                            response.write_saved = true;
                            let data = mailcraft_net::google_pim::download(&account, &valid_access);
                            response.contacts = data.contacts;
                            response.calendars = data.calendars;
                            response.events = data.events;
                            response.errors = data.errors;
                        }
                        Err(problem) => response.errors.push(problem),
                    }
                    return response;
                }
