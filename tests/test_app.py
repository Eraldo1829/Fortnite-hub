import os
import tempfile
import unittest
from unittest.mock import patch

_tmp = tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH'] = os.path.join(_tmp.name, 'test.db')
import app as hub

ITEM = {'id':'skin1','name':'Test Skin','image':'https://example.com/skin.png','price':1200,'bundle_items':[{'id':'skin1','name':'Test Skin'}]}
SHOP = {'data':{'date':'2026-10-19T00:00:00Z','entries':[]}}

class HubTests(unittest.TestCase):
    def setUp(self):
        hub.app.config['TESTING'] = True
        self.client = hub.app.test_client()
        self.mocks = [patch.object(hub, 'get_shop', return_value=SHOP),
                      patch.object(hub, 'prepare_shop', return_value=[dict(ITEM)]),
                      patch.object(hub, 'get_all_cosmetics', return_value=[dict(ITEM)]),
                      patch.object(hub, 'get_current_shop_prices', return_value={}),
                      patch.object(hub, 'api_get', return_value=None)]
        for mock in self.mocks:
            mock.start()
        self.addCleanup(patch.stopall)
        with hub.get_db() as conn:
            for table in ['sprite_collection','notification_log','notification_settings','favorites','users','shop_history']:
                conn.execute('DELETE FROM '+table)

    def login(self):
        self.client.post('/register', data={'username':'tester','email':'tester@example.com','password':'test-password'})
        self.client.post('/login', data={'username':'tester','password':'test-password'})

    def test_public_pages_and_offline_fallbacks(self):
        for path in ['/', '/skins','/all-items','/all-items/skin1','/skins/0','/players','/players?q=abc','/news','/leaks','/chests','/shop-history']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get('/shop-history/'+hub.get_shop_date()).status_code,200)
        self.assertEqual(self.client.get('/missing').status_code,404)

    def test_favorites_and_notifications(self):
        self.assertEqual(self.client.post('/api/favorite/toggle',json={'item_id':'skin1'}).status_code,401)
        self.login()
        self.assertTrue(self.client.post('/api/favorite/toggle',json={'item_id':'skin1','item_name':'Test Skin'}).json['is_favorite'])
        for path in ['/favorites','/favorites/skin1','/profile','/notifications']:
            self.assertEqual(self.client.get(path).status_code,200)
        self.client.post('/notifications',data={'enabled':'1','email_address':'test@example.com'})
        with hub.get_db() as conn:
            row=conn.execute('SELECT * FROM notification_settings').fetchone()
            self.assertEqual(row['enabled'],1)
        self.assertIn(b'indirizzo email valido',self.client.post('/notifications',data={'enabled':'1','email_address':'invalid'}).data)
        self.assertFalse(self.client.post('/api/favorite/toggle',json={'item_id':'skin1'}).json['is_favorite'])

    def test_cron_auth_and_notification_deduplication(self):
        self.assertEqual(self.client.get('/api/tracker/check').status_code,401)
        self.login()
        self.client.post('/api/favorite/toggle',json={'item_id':'skin1','item_name':'Test Skin'})
        self.client.post('/notifications',data={'enabled':'1','email_address':'test@example.com'})
        with patch.dict(os.environ,{'CRON_SECRET':'test-secret'}), patch('services.notification_service.send_skin_notification',return_value=True) as send:
            for _ in range(2):
                response=self.client.get('/api/tracker/check',headers={'X-Cron-Secret':'test-secret'})
                self.assertEqual(response.status_code,200)
            self.assertEqual(send.call_count,1)

    def test_export_is_private_and_excludes_other_users(self):
        self.assertEqual(self.client.get('/profile/favorites.json').status_code, 302)
        self.login()
        self.client.post('/api/favorite/toggle', json={'item_id': 'skin1', 'item_name': 'My Skin'})
        with hub.get_db() as conn:
            conn.execute("INSERT INTO users(username,password_hash,created_at) VALUES('other','hash','now')")
            other = conn.execute("SELECT id FROM users WHERE username='other'").fetchone()['id']
            conn.execute("INSERT INTO favorites(user_id,item_id,item_name,created_at) VALUES(?, 'private', 'Other skin', 'now')", (other,))
        response = self.client.get('/profile/favorites.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['item_id'] for item in response.json['favorites']], ['skin1'])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertIn('attachment', response.headers['Content-Disposition'])

    def test_email_configuration_and_safe_content(self):
        from services.notification_service import email_is_configured, send_skin_notification
        from services.email_service import send_welcome_email
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key', 'RESEND_FROM_EMAIL': ''}):
            self.assertFalse(email_is_configured())
            with patch('resend.Emails.send') as send:
                self.assertFalse(send_skin_notification('test@example.com', 'User', 'Skin'))
                self.assertFalse(send_welcome_email('test@example.com', 'User'))
                send.assert_not_called()
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key', 'RESEND_FROM_EMAIL': 'Hub <alerts@example.com>'}):
            with patch('resend.Emails.send', return_value={'id': 'test'}) as send:
                self.assertTrue(send_skin_notification('test@example.com', '<script>', 'Skin'))
                self.assertEqual(send.call_args.args[0]['from'], 'Hub <alerts@example.com>')
                self.assertIn('&lt;script&gt;', send.call_args.args[0]['html'])
                self.assertTrue(send_welcome_email('test@example.com', '<script>'))
                self.assertIn('&lt;script&gt;', send.call_args.args[0]['html'])

    def test_sprite_collection_validation_isolation_and_import(self):
        from services import sprite_catalog
        catalog = {'items': [{'id': 'water-base', 'name': 'Acqua', 'family': 'Acqua',
                    'style': 'base', 'released': True, 'active': True, 'archived': False,
                    'image': '', 'rarity': 'rare', 'name_official': True},
                    {'id': 'future-base', 'released': False}],
                   'checked_at': '2026-10-26T00:00:00Z', 'source': sprite_catalog.SOURCE, 'stale': False}
        with patch.object(sprite_catalog, 'get_catalog', return_value=catalog):
            self.assertEqual(self.client.get('/api/sprites/collection').status_code, 401)
            self.login()
            for data in [{'id': 'unknown', 'owned': True}, {'id': 'future-base', 'owned': True},
                         {'id': 'water-base', 'owned': 'false'}, {'ids': ['water-base', 'invalid']}]:
                self.assertEqual(self.client.post('/api/sprites/collection', json=data).status_code, 400)
            for _ in range(2):
                response = self.client.post('/api/sprites/collection', json={'id': 'water-base', 'owned': True})
                self.assertEqual(response.json['ids'], ['water-base'])
            self.assertEqual(self.client.get('/api/sprites/collection').headers['Cache-Control'], 'no-store')
            self.assertEqual(self.client.post('/api/sprites/collection', json={'id': 'water-base', 'owned': False}).json['ids'], [])
            self.assertEqual(self.client.post('/api/sprites/collection', json={'ids': ['water-base', 'water-base']}).json['ids'], ['water-base'])
            other = hub.app.test_client()
            other.post('/register', data={'username':'second', 'email':'second@example.com', 'password':'test-password'})
            other.post('/login', data={'username':'second', 'password':'test-password'})
            self.assertEqual(other.get('/api/sprites/collection').json['ids'], [])
            response = self.client.post('/api/sprites/collection', json={'id':'water-base','owned':True}, headers={'Origin':'https://evil.example'})
            self.assertEqual(response.status_code, 403)

    def test_sprite_snapshot_and_offline_catalog(self):
        import json
        from services import sprite_catalog as sc
        snapshot = json.loads(sc.SNAPSHOT.read_text())
        self.assertGreater(len(snapshot['items']), 250)
        self.assertEqual(len({x['id'] for x in snapshot['items']}), len(snapshot['items']))
        with patch.object(sc, '_cache', None), patch.object(sc, '_next_refresh', 0), patch.object(sc.requests, 'get', side_effect=sc.requests.Timeout):
            result = sc.get_catalog()
            self.assertTrue(result['stale'])
            self.assertEqual(result['checked_at'], snapshot['checked_at'])
            response = self.client.get('/sprites')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'sprite-catalog', response.data)
            self.assertIn(b'ultima copia verificata', response.data)
        with self.assertRaises(ValueError): sc.parse_catalog('no data')
        with self.assertRaises(ValueError): sc.parse_catalog('const SPIRITS = []')
        raw = [{'key': 'water-base', 'icon': 'javascript:alert(1)'}] * 20
        with self.assertRaises(ValueError): sc.parse_catalog('const SPIRITS = '+json.dumps(raw))

    def test_registration_and_actual_login_form_fields(self):
        response = self.client.post('/register', data={'username':'NewUser', 'email':'  Player@Example.com ', 'password':'Secret123'})
        self.assertEqual(response.status_code, 302)
        with hub.get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE username='NewUser'").fetchone()
            self.assertEqual(row['email'], 'player@example.com')
            self.assertNotEqual(row['password_hash'], 'Secret123')
        for fields in [{'identifier':'PLAYER@example.com'}, {'identifier':'NewUser'}, {'email':'player@example.com'}, {'username':'NewUser'}]:
            self.client.get('/logout')
            self.assertEqual(self.client.post('/login', data={**fields, 'password':'Secret123'}).status_code, 302)
            with self.client.session_transaction() as session:
                self.assertEqual(session['username'], 'NewUser')
        self.client.get('/logout')
        response = self.client.post('/login', data={'identifier':'player@example.com', 'password':'wrong'})
        self.assertIn(b'non corretti', response.data)
        for name, email in [('Another','PLAYER@example.com'), ('NewUser','another@example.com')]:
            response = self.client.post('/register', data={'username':name, 'email':email, 'password':'Secret123'})
            self.assertNotEqual(response.status_code, 302)
        self.assertIn(b'name="identifier"', self.client.get('/login').data)

    def test_legacy_user_and_additive_email_migration(self):
        with hub.get_db() as conn:
            conn.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                         ('legacy', hub.generate_password_hash('Legacy123'), hub.now_iso()))
        hub.init_db()
        self.assertEqual(self.client.post('/login', data={'identifier':'legacy', 'password':'Legacy123'}).status_code,302)
        with tempfile.TemporaryDirectory() as directory:
            old_path = os.path.join(directory, 'legacy.db')
            with hub.sqlite3.connect(old_path) as conn:
                conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
                conn.execute("INSERT INTO users VALUES(7,?,?,?)", ('olduser', hub.generate_password_hash('Old12345'), hub.now_iso()))
            with patch.object(hub, 'DATABASE', old_path):
                hub.init_db()
                hub.init_db()
                response = self.client.post('/login', data={'identifier':'olduser', 'password':'Old12345'})
                self.assertEqual(response.status_code, 302)
                with hub.get_db() as conn:
                    user = conn.execute("SELECT * FROM users WHERE id=7").fetchone()
                    self.assertEqual(user['username'], 'olduser')
                    self.assertIsNone(user['email'])
        for data in [{'username':'new', 'email':'invalid','password':'abcdef'},
                     {'username':'new', 'email':'new@example.com','password':'123'}]:
            self.assertNotEqual(self.client.post('/register', data=data).status_code,302)

    def test_live_data_templates(self):
        responses = {
            '/v2/news/br':{'data':{'motds':[{'title':'News','body':'Body','image':'https://example.com/image.png'}]}},
            '/v1/map':{'data':{'images':{'pois':'https://example.com/map.png'},'pois':[{'name':'POI'}]}},
            '/v2/cosmetics/new':{'data':{'items':{'br':[ITEM]}}},
            '/v2/stats/br/v2':{'data':{'account':{'name':'Player'},'stats':{'all':{'overall':{'wins':5}}}}},
        }
        with patch.object(hub,'api_get',side_effect=lambda endpoint,*a,**kw:responses[endpoint]):
            for path in ['/news','/chests','/leaks','/players?q=Player']:
                self.assertEqual(self.client.get(path).status_code,200)

if __name__ == '__main__':
    unittest.main()
