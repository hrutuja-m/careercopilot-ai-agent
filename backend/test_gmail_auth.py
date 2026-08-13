from services.gmail_auth import get_gmail_service

service = get_gmail_service()

profile = service.users().getProfile(userId="me").execute()

print("Gmail connected successfully!")
print("Email:", profile.get("emailAddress"))
print("Total messages:", profile.get("messagesTotal"))