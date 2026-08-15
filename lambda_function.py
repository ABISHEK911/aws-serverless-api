import json
import boto3
import uuid
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])


def lambda_handler(event, context):
    http_method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path_params = event.get('pathParameters') or {}
    note_id = path_params.get('id')

    try:
        if http_method == 'GET' and note_id:
            return get_note(note_id)
        elif http_method == 'GET':
            return list_notes()
        elif http_method == 'POST':
            body = json.loads(event.get('body') or '{}')
            return create_note(body)
        elif http_method == 'DELETE' and note_id:
            return delete_note(note_id)
        else:
            return response(400, {'error': 'Unsupported route or method'})
    except Exception as e:
        return response(500, {'error': str(e)})


def get_note(note_id):
    result = table.get_item(Key={'id': note_id})
    item = result.get('Item')
    if not item:
        return response(404, {'error': 'Note not found'})
    return response(200, item)


def list_notes():
    result = table.scan()
    return response(200, result.get('Items', []))


def create_note(body):
    note_id = str(uuid.uuid4())
    item = {
        'id': note_id,
        'title': body.get('title', ''),
        'content': body.get('content', '')
    }
    table.put_item(Item=item)
    return response(201, item)


def delete_note(note_id):
    table.delete_item(Key={'id': note_id})
    return response(200, {'message': f'Note {note_id} deleted'})


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body)
    }