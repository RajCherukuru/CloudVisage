__copyright__   = "Copyright 2024, VISA Lab"
__license__     = "MIT"

import os
import csv
import sys
import torch
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
from torchvision import datasets
from torch.utils.data import DataLoader
import boto3
import base64
import io
import json


# Initialize SQS client
sqs = boto3.client('sqs', region_name='us-east-1')

# URL of your SQS queue
req_queue_url = 'https://sqs.us-east-1.amazonaws.com/339712911709/1225507153-req-queue'
res_queue_url="https://sqs.us-east-1.amazonaws.com/339712911709/1225507153-resp-queue"

# Initialize S3 client
s3 = boto3.client('s3', region_name='us-east-1')

# S3 bucket name
input_bucket = '1225507153-in-bucket'
output_bucket = '1225507153-out-bucket'


mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embedding conversion

def save_image_to_s3(image_bytes, image_name):
    s3.put_object(Body=image_bytes, Bucket=output_bucket, Key=image_name)

def process_image_from_sqs(message_body):
    
    # decoded_message_body = base64.b64decode(message_body)

# Split the decoded message body into image name and image data
    print("this is the messag body", message_body)
    image_name= message_body.split('||')[0]
    image_data= message_body.split('||')[1]
    correlation_id=message_body.split('||')[2]

    s3input_name= image_name+".jpg"

    print(image_name)



    image_body= base64.b64decode(image_data)

    # Open the image file
    image_file = Image.open(io.BytesIO(image_body))

    # Save the image to the input S3 bucket
    s3.put_object(Bucket=input_bucket, Key=s3input_name, Body=image_body)

    # Perform face matching
    result = face_match(image_file, 'data.pt')
    print(result[0])

    data = {
    "image_name": image_name,
    "result": result[0],
    "correlation_id":correlation_id
    }

    json_data = json.dumps(data)

    
    output_value= result[0].encode('utf-8')



    s3.put_object(Bucket=output_bucket, Key=image_name, Body=output_value)

    # Send result back through SQS
    response = sqs.send_message(
        QueueUrl=res_queue_url,
        MessageBody=json_data
    )
    print("result is sent back", data)


def face_match(image, data_path): # image= PIL Image, data_path= location of data.pt
    # getting embedding matrix of the given image
    face, prob = mtcnn(image, return_prob=True) # returns cropped face and probability
    emb = resnet(face.unsqueeze(0)).detach() # detach is to make required gradient false

    saved_data = torch.load(data_path) # loading data.pt file
    embedding_list = saved_data[0] # getting embedding data
    name_list = saved_data[1] # getting list of names
    dist_list = [] # list of matched distances, minimum distance is used to identify the person

    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)

    idx_min = dist_list.index(min(dist_list))
    return (name_list[idx_min], min(dist_list))

    

def receive_and_process_messages():
    while True:
        # Receive messages from SQS queue
        response = sqs.receive_message(
            QueueUrl=req_queue_url,
            MaxNumberOfMessages=1,  # Maximum number of messages to retrieve
            VisibilityTimeout=30,     # How long the message is invisible after received (in seconds)
            WaitTimeSeconds=2       # Wait time for long polling (in seconds)
        )

        # print("message recived by the app tier", response['Messages'])

        # Check if messages are received
        if 'Messages' in response:
            for message in response['Messages']:
                # Process the message
                process_image_from_sqs(message['Body'])

                # Delete the message from the queue to remove it
                sqs.delete_message(
                    QueueUrl=req_queue_url,
                    ReceiptHandle=message['ReceiptHandle']
                )
        # else:
            # print("No messages received.")
            # break  # Break the loop if no messages are received

if __name__ == '__main__':
    

    receive_and_process_messages()