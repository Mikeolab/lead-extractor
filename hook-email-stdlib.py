# Runtime hook: force-load stdlib email before app.email (avoids ModuleNotFoundError for email.mime)
import sys
# Import stdlib email package so "from email.mime.text" resolves correctly
import email.mime.text  # noqa: F401
import email.mime.multipart  # noqa: F401
