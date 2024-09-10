import smtplib
from email.message import EmailMessage

class SendMail:

    def sendMail(self, email, otp):

        # Email details
        sender = "c3061458@hallam.shu.ac.uk"
        recipient = email
        subject = "Verification"
        body = "Your OTP is {}.".format(otp)

        # Create the email message
        email = EmailMessage()
        email["From"] = sender
        email["To"] = recipient
        email["Subject"] = subject
        email.set_content(body)

        # Connect to the Outlook SMTP server
        smtp_server = "smtp-mail.outlook.com"
        port = 587

        # Send the email
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Secure the connection
            server.login(sender, "H_ku1201")  # Login to your Outlook account
            server.send_message(email)  # Send the email

        print("Email sent successfully!")
