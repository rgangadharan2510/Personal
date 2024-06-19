import index

event = {
    "version": "0",
    "id": "37666ae6-48cf-4285-b4c6-a3320b38824a",
    "detail-type": "Scheduled Event",
    "source": "aws.scheduler",
    "account": "257676781382",
    "time": "2024-06-13T12:30:00Z",
    "region": "us-east-2",
    "resources": [
        "arn:aws:scheduler:us-east-2:257676781382:schedule/default/rg-patch-intimation"
    ],
    "detail": "{}"
}

context = ""
index.lambda_handler(event, context)
