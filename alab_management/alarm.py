import smtplib

class Alarm(object):
    def __init__(self, receivers: list=["bernardus_rendy@berkeley.edu"], sender_email: str="alabmanagement@gmail.com", password: str="rjuttalfbnvquyek"):
        self.sender_email = sender_email
        self.receivers_email = receivers
        self.password = password

    def send_email(self, message, category):
        """
        Sends an email to the receiver email address with the exception and category.
        Category is the type of exception that occured.
        Example:
            send_email(Exception, "Emergency")
            send_email(Exception, "Warning, program continues")
        """
        self.message = f"Subject: {category}\n\n{message}"
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.sender_email, self.password)
            for receiver_email in self.receivers_email:
                server.sendmail(self.sender_email, receiver_email, self.message)
