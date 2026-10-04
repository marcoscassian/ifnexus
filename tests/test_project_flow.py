import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'

from app import app
from controllers.projetos import crud
from extensions import db
from models import Projeto, ProjetoImagem, Usuario


class ProjectFlowTest(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SESSION_COOKIE_SECURE=False,
            SUAP_CLIENT_ID='test-client-id',
            SUAP_REDIRECT_URI=None,
            SUAP_BASE_URL='https://suap.ifrn.edu.br',
        )
        self.upload_dir = tempfile.TemporaryDirectory(dir='static/uploads')
        crud.PROJETOS_DIR = Path(self.upload_dir.name)
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()
            self.owner = Usuario(
                nome='Marcos Cassiano', email='marcos@ifrn.edu.br', senha='hash',
                tipo_usuario='Aluno', matricula='2026001',
            )
            self.coauthor = Usuario(
                nome='Alex Bruno', email='alex@ifrn.edu.br', senha='hash',
                tipo_usuario='Aluno', matricula='2026002',
            )
            self.advisor = Usuario(
                nome='Professora Ana', email='ana@ifrn.edu.br', senha='hash',
                tipo_usuario='Docente', matricula='10001',
            )
            db.session.add_all([self.owner, self.coauthor, self.advisor])
            db.session.commit()
            self.owner_id, self.coauthor_id, self.advisor_id = self.owner.id, self.coauthor.id, self.advisor.id
        self._login(self.owner_id)

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        self.upload_dir.cleanup()

    def _login(self, user_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True

    def _published_payload(self):
        return {
            'submit_action': 'publish',
            'titulo': 'Irriga IFRN',
            'subtitulo': 'Uso inteligente da água',
            'descricao': 'Uma solução para acompanhar e automatizar a irrigação.',
            'tipo': 'pesquisa',
            'curso': 'informatica',
            'status': 'desenvolvimento',
            'orientador_id': str(self.advisor_id),
            'autores_ids[]': [str(self.owner_id), str(self.coauthor_id)],
            'autores_tipos[]': ['principal', 'coautor'],
            'objetivos[]': ['Criar o protótipo', 'Medir a economia de água'],
            'metodologias[]': ['Pesquisa bibliográfica', 'Testes de campo'],
            'resultados': 'Protótipo funcional em validação.',
            'tecnologias[]': ['Python', 'Flask'],
            'links_tipos[]': ['github'],
            'links_urls[]': ['https://github.com/ifrn/irriga'],
            'imagens[]': (io.BytesIO(b'\x89PNG\r\n\x1a\nvalid-image'), 'capa.png'),
            'arquivos[]': (io.BytesIO(b'%PDF-1.4 valid-document'), 'relatorio.pdf'),
            'cover_new_index': '0',
        }

    def test_complete_publish_flow_persists_relations_and_renders(self):
        response = self.client.post('/criarprojeto', data=self._published_payload(), content_type='multipart/form-data')
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            project = Projeto.query.one()
            self.assertTrue(project.publicado)
            self.assertEqual(project.orientador_id, self.advisor_id)
            self.assertEqual(len(project.autores), 2)
            self.assertEqual([item.descricao for item in project.objetivos], ['Criar o protótipo', 'Medir a economia de água'])
            self.assertEqual(len(project.metodologias), 2)
            self.assertEqual({item.nome for item in project.tecnologias}, {'Python', 'Flask'})
            self.assertEqual(project.links[0].tipo, 'github')
            self.assertTrue(project.imagem_capa.is_capa)
            self.assertEqual(project.arquivos[0].nome_original, 'relatorio.pdf')
            project_id = project.id
        detail = self.client.get(f'/projeto/{project_id}')
        self.assertEqual(detail.status_code, 200)
        self.assertIn('Irriga IFRN'.encode(), detail.data)
        self.assertIn('Protótipo funcional'.encode(), detail.data)

        with app.app_context():
            project = db.session.get(Projeto, project_id)
            image_id = project.imagens[0].id
            file_id = project.arquivos[0].id
        edit_payload = self._published_payload()
        edit_payload.pop('imagens[]')
        edit_payload.pop('arquivos[]')
        edit_payload['titulo'] = 'Irriga IFRN 2.0'
        edit_payload['existing_image_ids[]'] = [str(image_id)]
        edit_payload['existing_file_ids[]'] = [str(file_id)]
        edit_payload['cover_existing_id'] = str(image_id)
        response = self.client.post(f'/editarprojeto/{project_id}', data=edit_payload)
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            project = db.session.get(Projeto, project_id)
            self.assertEqual(project.titulo, 'Irriga IFRN 2.0')
            self.assertEqual(len(project.imagens), 1)
            self.assertEqual(len(project.arquivos), 1)

    def test_draft_can_be_incomplete_and_is_hidden_from_public_listing(self):
        response = self.client.post('/criarprojeto', data={
            'submit_action': 'draft', 'titulo': 'Ideia inicial', 'status': 'ideia',
            'autores_ids[]': [str(self.owner_id)], 'autores_tipos[]': ['principal'],
        })
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            project = Projeto.query.one()
            self.assertFalse(project.publicado)
            project_id = project.id
        self.assertNotIn(b'Ideia inicial', self.client.get('/projetos').data)
        self.assertIn(b'Ideia inicial', self.client.get('/meus_projetos').data)
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(self.client.get(f'/projeto/{project_id}').status_code, 404)

    def test_publish_validation_returns_inline_errors(self):
        payload = self._published_payload()
        payload['titulo'] = ''
        payload['links_urls[]'] = ['javascript:alert(1)']
        response = self.client.post('/criarprojeto', data=payload, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 422)
        self.assertIn('Informe o título do projeto'.encode(), response.data)
        self.assertIn('URL completa'.encode(), response.data)
        with app.app_context():
            self.assertEqual(Projeto.query.count(), 0)

    def test_gallery_adapts_from_zero_to_more_than_four_images(self):
        for image_count in range(6):
            with app.app_context():
                project = Projeto(
                    titulo=f'Galeria {image_count}', descricao='Teste da galeria.',
                    tipo='pesquisa', curso='informatica', status='concluido',
                    publicado=True, usuario_id=self.owner_id,
                )
                db.session.add(project)
                db.session.flush()
                for index in range(image_count):
                    db.session.add(ProjetoImagem(
                        caminho=f'uploads/teste/imagem-{index}.png',
                        nome_original=f'imagem-{index}.png',
                        is_capa=index == 0, ordem=index, projeto_id=project.id,
                    ))
                db.session.commit()
                project_id = project.id

            response = self.client.get(f'/projeto/{project_id}')
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertEqual(html.count('data-gallery-index='), image_count)
            self.assertNotIn('cover-stage', html)
            self.assertNotIn('cover-navigation', html)
            if image_count == 0:
                self.assertNotIn('id="image-modal"', html)
            if image_count == 1:
                self.assertNotIn('id="modal-next"', html)
            if image_count == 5:
                self.assertEqual(html.count('gallery-item-hidden'), 1)
                self.assertIn('+1', html)
                self.assertIn("event.key === 'ArrowLeft'", html)
                self.assertIn("event.key === 'ArrowRight'", html)

            with app.app_context():
                db.session.delete(db.session.get(Projeto, project_id))
                db.session.commit()

    def test_suap_login_uses_public_environment_callback(self):
        response = self.client.get('/auth/login', base_url='https://ifnexus.vercel.app')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('https://ifnexus.vercel.app/auth/login', html)
        self.assertNotIn('127.0.0.1:5000/auth/login', html)

    @patch('controllers.auth.routes.requests.get')
    def test_suap_token_is_validated_by_backend_before_login(self, requests_get):
        suap_response = Mock(status_code=200)
        suap_response.raise_for_status.return_value = None
        suap_response.json.return_value = {
            'nome_usual': 'Usuário SUAP',
            'email': 'usuario@escolar.ifrn.edu.br',
            'matricula': '2026123456',
            'tipo_usuario': 'Aluno',
            'campus': {'nome': 'Campus Caicó'},
        }
        requests_get.return_value = suap_response

        response = self.client.post('/auth/login_suap_js', json={'access_token': 'valid-token'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['success'])
        requests_get.assert_called_once()
        self.assertEqual(
            requests_get.call_args.kwargs['headers']['Authorization'],
            'Bearer valid-token',
        )
        with app.app_context():
            usuario = Usuario.query.filter_by(email='usuario@escolar.ifrn.edu.br').one()
            self.assertEqual(usuario.campus, 'Campus Caicó')

    @patch('controllers.auth.routes.requests.get')
    def test_suap_rejects_unverified_browser_user_data(self, requests_get):
        response = self.client.post('/auth/login_suap_js', json={
            'user_data': {'nome': 'Usuário falso', 'email': 'falso@ifrn.edu.br'},
        })
        self.assertEqual(response.status_code, 400)
        requests_get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
