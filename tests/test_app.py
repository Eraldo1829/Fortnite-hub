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
            for table in ['notification_log','notification_settings','favorites','users','shop_history']:
                conn.execute('DELETE FROM '+table)

    def login(self):
        self.client.post('/register', data={'username':'tester','password':'test-password'})
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

    def test_live_data_templates(self):
        responses = {
            '/v2/news/br':{'data':{'motds':[{'title':'News','body':'Body','image':'https://example.com/image.png'}]}},
            '/v1/map':{'data':{'images':{'pois':'https://example.com/map.png'},'pois':{'list':[{'name':'POI'}]}}},
            '/v2/cosmetics/new':{'data':{'items':{'br':[ITEM]}}},
            '/v2/stats/br/v2':{'data':{'account':{'name':'Player'},'stats':{'all':{'overall':{'wins':5}}}}},
        }
        with patch.object(hub,'api_get',side_effect=lambda endpoint,*a,**kw:responses[endpoint]):
            for path in ['/news','/chests','/leaks','/players?q=Player']:
                self.assertEqual(self.client.get(path).status_code,200)

if __name__ == '__main__':
    unittest.main()
