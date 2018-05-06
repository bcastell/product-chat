import os
import requests
import phonenumbers
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from pymongo import MongoClient
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

customers = MongoClient().store.customers

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
my_phone_num = os.environ['TWILIO_PHONE_NUMBER']
analytics_key = os.environ['TEXT_ANALYTICS_KEY']
sentiment_url = os.environ['TEXT_ANALYTICS_SENTIMENT_URL']

@app.route('/sms', methods=['GET', 'POST'])
def sms_reply():
	"""Reply with dynamic SMS based on incoming SMS sentiment"""
	inc_body = request.values.get('Body', None)
	inc_from = request.values.get('From', None)

	headers = {'Ocp-Apim-Subscription-Key' : analytics_key}
	documents = {'documents' : [
		{'id' : '1', 'language' : 'en', 'text' : inc_body}
	]}
	results = requests.post(sentiment_url, headers=headers, json=documents)

	sentiments = results.json()
	sentiment_score = sentiments['documents'][0]['score']

	reply = MessagingResponse()

	customer = customers.find_one({'phone' : inc_from})

	if sentiment_score < 0.5:
		reply.message(customer['negative_response'])
	else:
		reply.message(customer['positive_response'])

	return str(reply)

@app.route('/', methods=['GET', 'POST'])
def index():
	"""Show dashboard and handle valid form submissions"""
	if request.method == 'POST':
		name = request.form.get('name')
		drink = request.form.get('drink')
		phone = request.form.get('phone')

		num = phonenumbers.parse(phone, 'US')
		customer_phone_num = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)

		first_msg = build_msg(request, 'first_message', name, drink)
		pos_resp = build_msg(request, 'positive_response', name, drink)
		neg_resp = build_msg(request, 'negative_response', name, drink)

		customer = {
			'name'				: name,
			'phone'				: customer_phone_num,
			'drink'				: drink,
			'first_message'		: first_msg,
			'positive_response' : pos_resp,
			'negative_response' : neg_resp
		}

		if customers.find({'phone' : customer_phone_num}).count() > 0:
			customers.delete_many({'phone' : customer_phone_num})

		customers.insert_one(customer)

		sms_client = Client(account_sid, auth_token)
		sms_client.messages.create(
			to=customer_phone_num,
			from_=my_phone_num,
			body=first_msg
		)

		return redirect(url_for('index',
			first_msg = request.form.get('first_message'),
			pos_resp = request.form.get('positive_response'),
			neg_resp = request.form.get('negative_response')
		))

	return render_template('home.html')

def build_msg(request, msg_type, name, drink):
	"""Personalize SMS by replacing tags with customer info"""
	msg = request.form.get(msg_type)

	msg = msg.replace('<firstName>', name)
	msg = msg.replace('<productType>', drink)

	return msg
