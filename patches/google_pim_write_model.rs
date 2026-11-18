/// Optional explicit Google edits. These are never generated from a download.
/// Deletion and bulk mutation are excluded from the first write-enabled revision.
#[derive(Clone, Debug)]
pub enum GooglePimEdit {
    NewContact { first: String, last: String, email: String },
    RenameContact { resource: String, etag: String, first: String, last: String },
    NewAppointment { title: String, start: String, end: String },
    RenameAppointment { calendar: String, event: String, etag: String, title: String },
}
