import smtplib
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class Alarm(object):
    def __init__(self, 
    receivers: list=["bernardus_rendy@berkeley.edu"], 
    sender_email: str="alabmanagement@gmail.com", 
    password: str="rjuttalfbnvquyek",
    slack_bot_token: str = "xoxb-53032848964-4821073683568-FYhkwk28JdAMEOwSGn9Gi2Pf",
    slack_channel: str = "C04PF6C68MR"
    ):
        self.sender_email = sender_email
        self.receivers_email = receivers
        self.password = password
        self.slack_bot_token = slack_bot_token
        self.slack_channel = slack_channel

    def alert(self,message,category,platforms=["email","slack"]):
        if "email" in platforms:
            self.send_email(message,category)
        if "slack" in platforms:
            self.send_slack_notification(message,category)

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
    
    def send_slack_notification(self, message, category):
        try:
            client = WebClient(token=self.slack_bot_token)
            response = client.chat_postMessage(
                channel=self.slack_channel,
                text=category+": "+message
            )
            print(response)
        except SlackApiError as e:
            print("Error : {}".format(e))