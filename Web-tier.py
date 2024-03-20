from flask import Flask, request, jsonify
import boto3
import base64
import werkzeug
import time
import threading
import uuid
import json

app = Flask(__name__)

# Initialize SQS client
sqs = boto3.client('sqs', region_name='us-east-1')

# URL of your SQS queues
req_queue_url = 'https://sqs.us-east-1.amazonaws.com/339712911709/1225507153-req-queue'
res_queue_url = 'https://sqs.us-east-1.amazonaws.com/339712911709/1225507153-resp-queue'

response_list = []

def receive_messages(correlation_id):
    print("***********************************")
    print(response_list)
    for response in response_list:
        if response['correlation_id'] == correlation_id:
            ans = response
            response_list.remove(response)
            return ans

    while True:
        try:
            # Receive messages from SQS queue
            response = sqs.receive_message(
                QueueUrl=res_queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20
            )
            
            if 'Messages' in response:
                messages = response['Messages']
                for message in messages:
                    # Process the message
                    print("Received message:", message['Body'])
                    message_body = json.loads(message['Body'])

                    response_list.append(message_body)
                    # Delete the message from the queue
                    sqs.delete_message(
                        QueueUrl=res_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
            for response in response_list:
                if response['correlation_id'] == correlation_id:
                    ans = response
                    response_list.remove(response)
                    return ans

        except Exception as e:
            print("Error:", e)


@app.route('/', methods=['POST'])
def handle_post():
    if 'inputFile' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['inputFile']
    if image_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    image_name = werkzeug.utils.secure_filename(image_file.filename).split('.')[0]
    image_data = image_file.read()
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    correlation_id = str(uuid.uuid4())

    message_body = f"{image_name}||{image_base64}||{correlation_id}"

    # Send image as message to SQS queue
    try:
        response = sqs.send_message(
            QueueUrl=req_queue_url,
            MessageBody=message_body
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
    
    received_message=receive_messages(correlation_id)
    result= received_message['result']
    

    print("this is the final result show to grader", received_message)

    # Return response
    return f"{image_name}:{result}" , 200

if __name__ == '__main__':

    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=8000)