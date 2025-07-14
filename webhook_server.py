# import os
# import json
# import logging
# from datetime import datetime
# from flask import Flask, request, jsonify, abort, make_response
# from flask_sqlalchemy import SQLAlchemy
# from flask_socketio import SocketIO

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(message)s'
# )
# logger = logging.getLogger(__name__)

# # Configuration
# DB_URL = os.getenv(
#     'DATABASE_URL',
#     'postgresql://milesight:Habitek2025@localhost:5432/milesight'
# )
# SECRET = os.getenv(
#     'MS_SECRET',
#     'h5B+0FgwDtKXDO3wuSPBoME1vB6ku7BK'
# )

# # Initialize Flask, SQLAlchemy & SocketIO
# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# db = SQLAlchemy(app)
# socketio = SocketIO(app, cors_allowed_origins='*')

# # Model to store sensor or camera data
# class DeviceData(db.Model):
#     __tablename__ = 'device_data'
#     id = db.Column(db.Integer, primary_key=True)
#     device_uuid = db.Column(db.String(64), nullable=False)
#     timestamp = db.Column(db.DateTime, nullable=False)
#     record_type = db.Column(db.String(32), nullable=False)
#     data = db.Column(db.JSON, nullable=False)

# # Ensure database tables exist (ignore insufficient privileges)
# with app.app_context():
#     try:
#         db.create_all()
#         logger.info('Database tables created or verified.')
#     except Exception as e:
#         msg = str(e).lower()
#         if 'permission denied' in msg or 'insufficient privilege' in msg:
#             logger.warning('Insufficient privileges to create tables, assuming they already exist.')
#         else:
#             logger.exception('Error creating database tables: %s', e)
#             raise

# # Stubbed signature verification (disabled)
# def verify_signature(req):
#     return True

# @app.route('/milesight-webhook', methods=['POST'])
# def webhook():
#     logger.info('Webhook received from %s', request.remote_addr)
#     headers = {k: v for k, v in request.headers.items()}
#     logger.info('Request headers: %s', json.dumps(headers, indent=2))

#     # Signature check (skipped)
#     if not verify_signature(request):
#         abort(401)

#     # Parse JSON payload
#     try:
#         raw = request.get_data() or b''
#         payload = json.loads(raw)
#         logger.info('Payload JSON parsed')
#     except Exception as e:
#         logger.exception('JSON parsing error: %s', e)
#         abort(400)

#     events = payload if isinstance(payload, list) else [payload]
#     inserted = 0

#     # Process events and emit via WebSocket
#     for evt in events:
#         try:
#             data = evt.get('data', {}) or {}
#             profile = data.get('deviceProfile', {})
#             device_uuid = profile.get('devEUI') or profile.get('sn')
#             if not device_uuid:
#                 logger.warning('Skipping event: missing device identifier')
#                 continue

#             ts_ms = data.get('ts') or (evt.get('eventCreatedTime', 0) * 1000)
#             timestamp = datetime.utcfromtimestamp(ts_ms / 1000)

#             section = data.get('payload', {}) or {}
#             values = section.get('values', section)

#             if 'image' in values or 'snapType' in values:
#                 record_type = 'camera'
#             elif 'temperature' in values or 'humidity' in values:
#                 record_type = 'sensor'
#             else:
#                 record_type = 'unknown'

#             log_entry = {
#                 'device_uuid': device_uuid,
#                 'timestamp': timestamp.isoformat() + 'Z',
#                 'record_type': record_type,
#                 'values': values
#             }
#                         # Log parsed fields as a list
#             logger.info('Parsed event:')
#             logger.info('  device_uuid: %s', device_uuid)
#             logger.info('  timestamp: %s', timestamp.isoformat() + 'Z')
#             logger.info('  record_type: %s', record_type)
#             for key, val in values.items():
#                 logger.info('  %s: %s', key, val)

#             # Persist to database
#             rec = DeviceData(
#                 device_uuid=device_uuid,
#                 timestamp=timestamp,
#                 record_type=record_type,
#                 data=values
#             )
#             db.session.add(rec)
#             inserted += 1

#             # Emit real-time update
#             logger.info("Emitting new_data to clients: %s", log_entry)
#             socketio.emit('new_data', log_entry)
#         except Exception as e:
#             logger.exception('Error processing event: %s', e)

#     # Commit to DB
#     try:
#         db.session.commit()
#         logger.info('Committed %d records to database', inserted)
#     except Exception as e:
#         db.session.rollback()
#         logger.exception('Database commit error: %s', e)
#         abort(500)

#     return jsonify({'status': 'OK', 'inserted': inserted}), 200

# # Helper for pretty JSON response
# def pretty_response(obj):
#     text = json.dumps(obj, indent=2, ensure_ascii=False)
#     resp = make_response(text)
#     resp.mimetype = 'application/json'
#     return resp

# @app.route('/api/latest', methods=['GET'])
# def get_latest():
#     try:
#         rec = DeviceData.query.order_by(DeviceData.timestamp.desc()).first()
#         if not rec:
#             abort(404)
#         result = {
#             'device_uuid': rec.device_uuid,
#             'timestamp': rec.timestamp.isoformat() + 'Z',
#             'record_type': rec.record_type,
#             'data': rec.data
#         }
#         return pretty_response(result)
#     except Exception as e:
#         logger.exception('Latest API error: %s', e)
#         abort(500)

# @app.route('/api/history', methods=['GET'])
# def get_history():
#     try:
#         limit = min(request.args.get('limit', 100, type=int), 1000)
#         recs = DeviceData.query.order_by(DeviceData.timestamp.desc()).limit(limit).all()
#         items = []
#         for r in recs:
#             items.append({
#                 'device_uuid': r.device_uuid,
#                 'timestamp': r.timestamp.isoformat() + 'Z',
#                 'record_type': r.record_type,
#                 'data': r.data
#             })
#         return pretty_response(items)
#     except Exception as e:
#         logger.exception('History API error: %s', e)
#         abort(500)

# if __name__ == '__main__':
#     port = int(os.getenv('PORT', 4567))
#     logger.info('Starting server on port %d', port)
#     socketio.run(app, host='0.0.0.0', port=port)


import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS # Import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://milesight:Habitek2025@localhost:5432/milesight'
)
SECRET = os.getenv(
    'MS_SECRET',
    'h5B+0FgwDtKXDO3wuSPBoME1vB6ku7BK'
)

# Initialize Flask, SQLAlchemy & SocketIO
app = Flask(__name__)
CORS(app) # Enable CORS for all routes
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*') # Note: socketio already has cors_allowed_origins

# Model to store sensor or camera data
class DeviceData(db.Model):
    __tablename__ = 'device_data'
    id = db.Column(db.Integer, primary_key=True)
    device_uuid = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    record_type = db.Column(db.String(32), nullable=False)
    data = db.Column(db.JSON, nullable=False)


# Ensure database tables exist (ignore insufficient privileges)
with app.app_context():
    try:
        db.create_all()
        logger.info('Database tables created or verified.')
    except Exception as e:
        msg = str(e).lower()
        if 'permission denied' in msg or 'insufficient privilege' in msg:
            logger.warning('Insufficient privileges to create tables, assuming they already exist.')
        else:
            logger.exception('Error creating database tables: %s', e)
            raise

# Stubbed signature verification (disabled)
def verify_signature(req):
    return True

@app.route('/milesight-webhook', methods=['POST'])
def webhook():
    logger.info('Webhook received from %s', request.remote_addr)
    headers = {k: v for k, v in request.headers.items()}
    logger.info('Request headers: %s', json.dumps(headers, indent=2))

    # Signature check (skipped)
    if not verify_signature(request):
        abort(401)

    # Parse JSON payload
    try:
        raw = request.get_data() or b''
        payload = json.loads(raw)
        logger.info('Payload JSON parsed')
    except Exception as e:
        logger.exception('JSON parsing error: %s', e)
        abort(400)

    events = payload if isinstance(payload, list) else [payload]
    inserted = 0

    # Process events and emit via WebSocket
    for evt in events:
        try:
            data = evt.get('data', {}) or {}
            profile = data.get('deviceProfile', {})
            device_uuid = profile.get('devEUI') or profile.get('sn')
            if not device_uuid:
                logger.warning('Skipping event: missing device identifier')
                continue

            ts_ms = data.get('ts') or (evt.get('eventCreatedTime', 0) * 1000)
            timestamp = datetime.utcfromtimestamp(ts_ms / 1000)

            section = data.get('payload', {}) or {}
            values = section.get('values', section)

            if 'image' in values or 'snapType' in values:
                record_type = 'camera'
            elif 'temperature' in values or 'humidity' in values:
                record_type = 'sensor'
            else:
                record_type = 'unknown'

            log_entry = {
                'device_uuid': device_uuid,
                'timestamp': timestamp.isoformat() + 'Z',
                'record_type': record_type,
                'values': values
            }
                        # Log parsed fields as a list
            logger.info('Parsed event:')
            logger.info('  device_uuid: %s', device_uuid)
            logger.info('  timestamp: %s', timestamp.isoformat() + 'Z')
            logger.info('  record_type: %s', record_type)
            for key, val in values.items():
                logger.info('  %s: %s', key, val)

            # Persist to database
            rec = DeviceData(
                device_uuid=device_uuid,
                timestamp=timestamp,
                record_type=record_type,
                data=values
            )
            db.session.add(rec)
            inserted += 1

            # Emit real-time update
            logger.info("Emitting new_data to clients: %s", log_entry)
            socketio.emit('new_data', log_entry)
        except Exception as e:
            logger.exception('Error processing event: %s', e)

    # Commit to DB
    try:
        db.session.commit()
        logger.info('Committed %d records to database', inserted)
    except Exception as e:
        db.session.rollback()
        logger.exception('Database commit error: %s', e)
        abort(500)

    return jsonify({'status': 'OK', 'inserted': inserted}), 200

# Helper for pretty JSON response
def pretty_response(obj):
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    resp = make_response(text)
    resp.mimetype = 'application/json'
    return resp

@app.route('/api/latest', methods=['GET'])
def get_latest():
    try:
        rec = DeviceData.query.order_by(DeviceData.timestamp.desc()).first()
        if not rec:
            abort(404)
        result = {
            'device_uuid': rec.device_uuid,
            'timestamp': rec.timestamp.isoformat() + 'Z',
            'record_type': rec.record_type,
            'data': rec.data
        }
        return pretty_response(result)
    except Exception as e:
        logger.exception('Latest API error: %s', e)
        abort(500)

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        limit = min(request.args.get('limit', 100, type=int), 1000)
        recs = DeviceData.query.order_by(DeviceData.timestamp.desc()).limit(limit).all()
        items = []
        for r in recs:
            items.append({
                'device_uuid': r.device_uuid,
                'timestamp': r.timestamp.isoformat() + 'Z',
                'record_type': r.record_type,
                'data': r.data
            })
        return pretty_response(items)
    except Exception as e:
        logger.exception('History API error: %s', e)
        abort(500)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 4567))
    logger.info('Starting server on port %d', port)
    socketio.run(app, host='0.0.0.0', port=port)