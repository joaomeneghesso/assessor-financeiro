import unittest

import assessor_orientacao as orient
import services as svc
import telegram_experiencia as ux


def flatten(rows):
    for row in rows:
        for item in row:
            yield item


class HelpV393Tests(unittest.TestCase):
    def test_01_version(self):
        self.assertEqual(ux.VERSION, '4.2.0')

    def test_02_root_has_only_six_paths_plus_home(self):
        e = ux.Experience()
        screen = e.screen_help(e.session('root'))
        labels = [x for x, _ in flatten(screen.rows)]
        expected = [
            '🚀 Começar', '➕ Registrar', '💳 Pagar e faturas',
            '💰 Entender meu dinheiro', '🔎 Consultar e corrigir', '⚙️ Mais recursos',
        ]
        for label in expected:
            self.assertIn(label, labels)
        self.assertIn('🏠 Início', labels)
        self.assertIn('🧭 Ver todos os recursos', labels)
        self.assertEqual(len(labels), 8)
        self.assertIn('6 caminhos', screen.text)

    def test_03_group_payments_coverage(self):
        labels = [x for x, _ in flatten(ux.HELP_TOPICS['grupo_pagar']['rows'])]
        for label in ['💳 Faturas', '🧾 Pagar', '🧾 Fixos e previsões', '🔗 Conciliação']:
            self.assertIn(label, labels)

    def test_04_group_money_coverage(self):
        labels = [x for x, _ in flatten(ux.HELP_TOPICS['grupo_dinheiro']['rows'])]
        for label in ['💰 Saldo e caixa', '📊 Analisar/auditar', '📋 Fechamento', '🧭 Planejar']:
            self.assertIn(label, labels)

    def test_05_group_consult_coverage(self):
        labels = [x for x, _ in flatten(ux.HELP_TOPICS['grupo_consultar']['rows'])]
        for label in ['🔎 Histórico', '✏️ Corrigir', '🔁 Transferências', '💵 Receber']:
            self.assertIn(label, labels)

    def test_06_group_more_coverage(self):
        labels = [x for x, _ in flatten(ux.HELP_TOPICS['grupo_mais']['rows'])]
        for label in ['🔔 Alertas', '🤖 IA / Ollama', '🔐 Dados e segurança', '⌨️ Comandos avançados', '🎓 Aprender']:
            self.assertIn(label, labels)

    def test_07_leaf_topics_still_exist(self):
        for key in ['primeiros','registrar','compromissos','pagar','receber','faturas','transferencias','saldo','historico','analisar','corrigir','conciliar','planejar','alertas','controle','ia','dados','privacidade']:
            with self.subTest(topic=key):
                self.assertIn(key, ux.HELP_TOPICS)

    def test_08_topic_structure(self):
        self.assertGreaterEqual(len(ux.HELP_TOPICS), 22)
        for key, data in ux.HELP_TOPICS.items():
            with self.subTest(topic=key):
                self.assertTrue(data['title'].strip())
                self.assertGreaterEqual(len(data['body'].strip()), 40)
                self.assertTrue(data['rows'])

    def test_09_view_actions_exist(self):
        for key, data in ux.HELP_TOPICS.items():
            for label, action in flatten(data['rows']):
                if action[0] == 'view':
                    with self.subTest(topic=key, label=label):
                        self.assertTrue(callable(getattr(ux.Experience, 'screen_' + action[1], None)))

    def test_10_topic_actions_exist(self):
        for key, data in ux.HELP_TOPICS.items():
            for label, action in flatten(data['rows']):
                if action[0] == 'topic':
                    with self.subTest(topic=key, label=label):
                        self.assertTrue(action[1] in ux.HELP_TOPICS or action[1] in orient.TOPICS)

    def test_11_group_screens_render(self):
        e = ux.Experience()
        for key in ['grupo_pagar','grupo_dinheiro','grupo_consultar','grupo_mais']:
            s = e.session('group-' + key)
            s.topic = key
            screen = e.screen_help_topic(s)
            self.assertTrue(screen.text)
            destinos = [a for _, a in flatten(screen.rows)]
            self.assertIn(('view', 'help'), destinos)  # volta à Central de ajuda

    def test_12_leaf_back_navigation_goes_to_parent_group(self):
        e = ux.Experience()
        for leaf, (parent, back_label) in ux.HELP_PARENT.items():
            if leaf not in ux.HELP_TOPICS:
                continue
            s = e.session('leaf-' + leaf)
            s.topic = leaf
            screen = e.screen_help_topic(s)
            destinos = [a for _, a in flatten(screen.rows)]
            self.assertIn(('topic', parent), destinos)  # volta ao grupo pai

    def test_13_parent_targets_are_valid_groups(self):
        for leaf, (parent, _) in ux.HELP_PARENT.items():
            self.assertIn(leaf, ux.HELP_TOPICS)
            self.assertIn(parent, {'grupo_pagar','grupo_dinheiro','grupo_consultar','grupo_mais'})
            self.assertIn(parent, ux.HELP_TOPICS)

    def test_14_no_duplicate_leaf_in_multiple_groups(self):
        seen = {}
        for group in ['grupo_pagar','grupo_dinheiro','grupo_consultar','grupo_mais']:
            for _, action in flatten(ux.HELP_TOPICS[group]['rows']):
                if action[0] != 'topic':
                    continue
                leaf = action[1]
                self.assertNotIn(leaf, seen, f'{leaf} repetido em {seen.get(leaf)} e {group}')
                seen[leaf] = group

    def test_15_fatura_v39_rule_preserved(self):
        text = ux.HELP_TOPICS['faturas']['body'].lower()
        lesson = svc.montar_aula_faturas().lower()
        self.assertIn('dia 25', text)
        self.assertIn('data da compra', text)
        self.assertIn('competência', text)
        self.assertIn('25/09', lesson)
        self.assertIn('fatura outubro', lesson)

    def test_16_registration_teaches_installments(self):
        text = ux.HELP_TOPICS['registrar']['body'].lower()
        self.assertIn('parcelamento', text)
        self.assertIn('dia 25', text)
        self.assertIn('data real', text)

    def test_17_learning_menu_coverage(self):
        menu = svc.montar_aprender_menu().lower()
        for term in ['faturas e fechamento','transferências','fixos e entradas previstas','conciliação','planejamento e limites','auditoria e correções','dados, backup e segurança','rotina diária']:
            with self.subTest(term=term):
                self.assertIn(term, menu)

    def test_18_numbered_lessons(self):
        for n in range(1, 17):
            with self.subTest(n=n):
                self.assertTrue(svc.montar_aprender_tema(str(n)).startswith('🎓 Aula:'))

    def test_19_help_is_read_only(self):
        e = ux.Experience()
        self.assertIn('consultas não alteram registros', e.screen_help(e.session('readonly')).text.lower())

    def test_20_all_help_texts_fit_telegram(self):
        e = ux.Experience()
        root = e.screen_help(e.session('size-root')).text
        self.assertLess(len(root.encode('utf-16-le')) // 2, 3900)
        for key in ux.HELP_TOPICS:
            s = e.session('size-' + key)
            s.topic = key
            text = e.screen_help_topic(s).text
            with self.subTest(topic=key):
                self.assertLess(len(text.encode('utf-16-le')) // 2, 3900)

    def test_21_help_preserves_paused_draft(self):
        e = ux.Experience(); s = e.session('draft')
        s.view='register'; s.stage='amount'; s.draft={'tipo':'despesa','descricao':'teste'}
        original=dict(s.draft)
        self.assertTrue(e._suspend_flow(s)); e.screen_help(s)
        self.assertEqual(s.suspended_draft, original)
        self.assertEqual(s.suspended_stage, 'amount')
        self.assertIsNone(s.draft)

    def test_22_no_audio_reintroduced(self):
        text='\n'.join(d['title']+'\n'+d['body'] for d in ux.HELP_TOPICS.values()).lower()
        self.assertNotIn('áudio',text); self.assertNotIn('audio',text); self.assertNotIn('voz',text)

    def test_23_commands_advanced_still_reachable(self):
        action_map = dict(flatten(ux.HELP_TOPICS['grupo_mais']['rows']))
        self.assertEqual(action_map['⌨️ Comandos avançados'], ('view','command_help'))
        e=ux.Experience(); self.assertTrue(e.screen_command_help(e.session('cmd')).text)

    def test_24_learning_still_reachable(self):
        action_map = dict(flatten(ux.HELP_TOPICS['grupo_mais']['rows']))
        self.assertEqual(action_map['🎓 Aprender'], ('legacy','aprender'))
        self.assertTrue(svc.processar_mensagem('aprender').startswith('🎓 '))

    def test_25_root_does_not_dump_leaf_topics(self):
        labels = [x for x,_ in flatten(ux.Experience().screen_help(ux.Experience().session('x')).rows)]
        for hidden in ['🧾 Fixos e previsões','💳 Faturas','🔁 Transferências','💰 Saldo e caixa','🔎 Histórico','📊 Analisar/auditar','✏️ Corrigir','🔗 Conciliação','🧭 Planejar','🔔 Alertas','📋 Fechamento','🤖 IA / Ollama','🔐 Dados e segurança','🎓 Aprender','⌨️ Comandos avançados']:
            self.assertNotIn(hidden, labels)

    def test_26_group_titles_are_goal_oriented(self):
        for key in ['grupo_pagar','grupo_dinheiro','grupo_consultar','grupo_mais']:
            title=ux.HELP_TOPICS[key]['title']
            self.assertGreaterEqual(len(title.split()),2)

    def test_27_privacy_back_goes_to_more_resources(self):
        e=ux.Experience(); s=e.session('privacy'); s.topic='privacidade'
        destinos=[a for _,a in flatten(e.screen_help_topic(s).rows)]
        self.assertIn(('topic','grupo_mais'),destinos)

    def test_28_help_groups_are_non_writing_navigation(self):
        for group in ['grupo_pagar','grupo_dinheiro','grupo_consultar','grupo_mais']:
            for _, action in flatten(ux.HELP_TOPICS[group]['rows']):
                self.assertNotIn(action[0], {'commit','save','delete','undo','invoice_commit'})


if __name__ == '__main__':
    unittest.main()
