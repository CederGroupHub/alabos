import smtplib
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class Alarm(object):
    def __init__(self, 
    email_receivers = None, 
    email_sender = None, 
    email_password = None,
    slack_bot_token = None,
    slack_channel = None
    ):
        self.email_alert = False
        self.slack_alert = False
        if email_receivers is not None:
            try:
                self.setup_email(email_sender, email_receivers, email_password)
                self.email_alert=True
            except:
                print("Email setup failed, please recheck config file")
        if slack_bot_token is not None:
            try:
                self.setup_slack(slack_bot_token, slack_channel)
                self.slack_alert=True
            except:
                print("Slackbot setup failed, please recheck config file")
        self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
    
    def setup_email(self, email_receivers, email_sender, email_password):
        try:
            self.email_receivers = email_receivers
            self.email_sender = email_sender
            self.email_password = email_password
            self.email_alert=True
            self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
        except:
            print("Email setup failed, please recheck config file")
    
    def setup_slackbot(self, slack_bot_token, slack_channel):
        try:
            self.slack_bot_token = slack_bot_token
            self.slack_channel = slack_channel
            self.slack_alert=True
            self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
        except:
            print("Slackbot setup failed, please recheck config file")

    def alert(self,message,category):
        try:
            if self.platforms["email"]:
                self.send_email(message,category)
            if self.platforms["slack"]:
                self.send_slack_notification(message,category)
        except:
            if self.platforms["slack"]:
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
            server.login(self.email_sender, self.email_password)
            for receiver in self.email_receivers:
                server.sendmail(self.email_sender, receiver, self.message)
    
    def send_slack_notification(self, message, category):
        try:
            client = WebClient(token=self.slack_bot_token)
            response = client.chat_postMessage(
                channel=self.slack_channel,
                text=category+": "+message
            )
            # print(response)
        except SlackApiError as e:
            print("Error : {}".format(e))