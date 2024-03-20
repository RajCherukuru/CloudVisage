import boto3
import time

instance_list=[]

sqs = boto3.client('sqs', region_name='us-east-1')
ec2 = boto3.client('ec2', region_name='us-east-1')

key_pair="developer_key"
iam_instance_profile_arn="arn:aws:iam::339712911709:instance-profile/SQS_S3fullaccess"

def get_queue_length(queue_url):
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes']['ApproximateNumberOfMessages'])

def terminate_instance(instance_id):
    ec2.terminate_instances(InstanceIds=[instance_id])

def create_instance(instance_name):
    response = ec2.run_instances(
        ImageId='ami-09c546ac15d041066',
        InstanceType='t2.micro',
        KeyName=key_pair,
        IamInstanceProfile={'Arn': iam_instance_profile_arn},
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ]
    )
    print("inside the create instance ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    instance_id = response['Instances'][0]['InstanceId']
    instance_list.append(instance_id)
    return instance_id

def main():
    queue_url = 'https://sqs.us-east-1.amazonaws.com/339712911709/1225507153-req-queue'


    while True:
        queue_length = get_queue_length(queue_url)

        print(queue_length)
        print(instance_list)

        if queue_length==0:
            numberofinstance= len(instance_list)
            for i in range(numberofinstance):
                recent_instance_id= instance_list.pop()
                terminate_instance(recent_instance_id)

        elif queue_length <= 10:
            numberofinstance= len(instance_list)
            extra= 10-numberofinstance
            for i in range(extra):
                    instance_name= f"app-tier-instance-{numberofinstance+i+1}"
                    print(instance_name)
                    create_instance(instance_name)



        elif queue_length > 10:
            numberofinstance= len(instance_list)
            extra= 20-numberofinstance
            for i in range(extra):
                    instance_name= f"app-tier-instance-{numberofinstance+i+1}"
                    print(instance_name)
                    create_instance(instance_name)

        
        time.sleep(30)  # Check every minute

if __name__ == "__main__":
    main()
