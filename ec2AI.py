import cv2
import boto3
import time
import logging
from cvzone.HandTrackingModule import HandDetector

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize AWS resources
ec2 = boto3.resource('ec2', region_name='ap-south-1')
elb = boto3.client('elbv2', region_name='ap-south-1')
allOS = []

def LaunchOS():
    try:
        logging.info("Launching EC2 instance...")
        instances = ec2.create_instances(
            ImageId="ami-0cc9838aa7ab1dce7",
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            SecurityGroupIds=['sg-0bb421c553a3bd4e6']  # Default VPC's security group
        )

        OSid = instances[0].id
        allOS.append(OSid)
        logging.info(f"EC2 instance launched with ID: {OSid}")
        
        time.sleep(30)
        elb.register_targets(
            TargetGroupArn='arn:aws:elasticloadbalancing:ap-south-1:881559863141:targetgroup/testtg/5eb53fb428255398',
            Targets=[{'Id': OSid}]
        )
        logging.info("Instance registered with ELB target group.")
    except Exception as e:
        logging.error(f"Failed to launch EC2 instance: {e}")

def TerminateOS():
    if allOS:
        try:
            myos = allOS.pop()
            logging.info(f"Terminating EC2 instance with ID: {myos}")
            response = ec2.instances.filter(InstanceIds=[myos]).terminate()
            
            elb.deregister_targets(
                TargetGroupArn='arn:aws:elasticloadbalancing:ap-south-1:881559863141:targetgroup/testtg/5eb53fb428255398',
                Targets=[{'Id': myos}]
            )
            logging.info("Instance deregistered from ELB target group.")
            logging.info("Remaining OS: " + str(len(allOS)))
            return response
        except Exception as e:
            logging.error(f"Failed to terminate EC2 instance: {e}")
    else:
        logging.info("No more OS is running")

# Initialize hand detector
detector = HandDetector(maxHands=1, detectionCon=0.8)

# Initialize video capture
cap = cv2.VideoCapture(0)

while True:
    ret, img = cap.read()
    if not ret:
        logging.error("Failed to capture image from webcam.")
        break
    
    cv2.imshow("Img", img)
    
    if cv2.waitKey(1) & 0xFF == 13:  # Press Enter to exit
        break

    hands, img = detector.findHands(img, draw=False)
    if hands:
        for myHand in hands:  # Iterate over detected hands
            lmlist = myHand['lmList']
            if lmlist:
                fingerup = detector.fingersUp(myHand)
                logging.info(f"Detected finger pattern: {fingerup}")
                if fingerup == [0, 1, 0, 0, 0]:
                    logging.info("Detected gesture to terminate instance.")
                    TerminateOS()
                elif fingerup == [0, 1, 1, 0, 0]:
                    logging.info("Detected gesture to launch instance.")
                    LaunchOS()

cap.release()
cv2.destroyAllWindows()
