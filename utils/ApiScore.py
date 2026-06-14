import requests
import json
from datetime import datetime

class ScoreAPIClient:
    def __init__(self, base_url="http://tomcat03.COMPANY_NAME.com.br:8081"):
        self.base_url = base_url
        self.token = None
        self.headers = {'Content-Type': 'application/json'}
    

    def login(self, username, password):
        """
        Faz login na API e obtém o token JWT
        """
        try:
            url = f"{self.base_url}/auth"
            data = {
                "login": username,
                "senha": password
            }
            
            print(f"Fazendo login para usuário: {username}")
            response = requests.post(url, json=data, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                self.token = result.get('token')
                
                # Adiciona o token no header para próximas requisições
                self.headers['Authorization'] = f'Bearer {self.token}'
                
                print("Login realizado com sucesso!")
                print(f"Token obtido: {self.token[:50]}...")
                return True
            else:
                print(f"Erro no login: {response.status_code}")
                print(response.text)
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão no login: {e}")
            return False
    
    def cadastrar_categoria(self, descricao):
        """
        Cadastra uma nova categoria de score
        """
        try:
            url = f"{self.base_url}/score/categoria/cadastrar"
            data = {"dsCategoria": descricao}
            
            print(f"Cadastrando categoria: {descricao}")
            response = requests.post(url, json=data, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    categoria_id = result['conteudo']['cdCategoria']
                    print(f"Categoria cadastrada! ID: {categoria_id}")
                    return categoria_id
                else:
                    print(f"Erro: {result['mensagem']}")
                    return None
            else:
                print(f"Erro HTTP: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return None
    
    def cadastrar_indicador(self, descricao):
        """
        Cadastra um novo indicador de score
        """
        try:
            url = f"{self.base_url}/score/indicador/cadastrar"
            data = {"dsIndicador": descricao}
            
            print(f"Cadastrando indicador: {descricao}")
            response = requests.post(url, json=data, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    indicador_id = result['conteudo']['cdIndicador']
                    print(f"Indicador cadastrado! ID: {indicador_id}")
                    return indicador_id
                else:
                    print(f"Erro: {result['mensagem']}")
                    return None
            else:
                print(f"Erro HTTP: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return None
    
    def cadastrar_peso(self, categoria_id, indicador_id, peso):
        """
        Cadastra um peso relacionando categoria e indicador
        """
        try:
            url = f"{self.base_url}/score/peso/cadastrar"
            data = {
                "cdCategoria": categoria_id,
                "cdIndicador": indicador_id,
                "pcPeso": peso
            }
            
            print(f"Cadastrando peso: Categoria {categoria_id} + Indicador {indicador_id} = {peso}%")
            response = requests.post(url, json=data, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    print("Peso cadastrado com sucesso!")
                    return True
                else:
                    print(f"Erro: {result['mensagem']}")
                    return False
            else:
                print(f"Erro HTTP: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return False
    
    def cadastrar_score(self, cliente_id, score):
        """
        Cadastra ou atualiza o score de um cliente
        """
        try:
            url = f"{self.base_url}/score/cadastrar"
            data = {
                "cdCliente": cliente_id,
                "dcScore": score
            }
            
            print(f"Cadastrando score: Cliente {cliente_id} = {score}")
            response = requests.post(url, json=data, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    print("Score cadastrado com sucesso!")
                    return True
                else:
                    print(f"Erro: {result['mensagem']}")
                    return False
            else:
                print(f"Erro HTTP: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return False
    
    def consultar_score(self, cliente_id):
        """
        Consulta o score de um cliente
        """
        try:
            url = f"{self.base_url}/score/{cliente_id}"
            
            print(f"Consultando score do cliente: {cliente_id}")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    score = result['conteudo']['dcScore']
                    print(f"Score encontrado: {score}")
                    return score
                else:
                    print(f"Erro: {result['mensagem']}")
                    return None
            else:
                print(f"Erro HTTP: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return None
    
    def listar_categorias(self):
        """
        Lista todas as categorias
        """
        try:
            url = f"{self.base_url}/score/categoria/listar"
            
            print("Listando categorias...")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    categorias = result['conteudo']
                    print(f"{len(categorias)} categorias encontradas:")
                    for cat in categorias:
                        print(f"   - ID: {cat['cdCategoria']} | {cat['dsCategoria']}")
                    return categorias
                else:
                    print(f"Erro: {result['mensagem']}")
                    return []
            else:
                print(f"Erro HTTP: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return []
    
    def listar_indicadores(self):
        """
        Lista todos os indicadores
        """
        try:
            url = f"{self.base_url}/score/indicador/listar"
            
            print("Listando indicadores...")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    indicadores = result['conteudo']
                    print(f"{len(indicadores)} indicadores encontrados:")
                    for ind in indicadores:
                        print(f"   - ID: {ind['cdIndicador']} | {ind['dsIndicador']}")
                    return indicadores
                else:
                    print(f"Erro: {result['mensagem']}")
                    return []
            else:
                print(f"Erro HTTP: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return []
    
    def listar_categorias_indicadores_pesos(self):
        """
        Lista todas as categorias, indicadores e pesos configurados
        """
        try:
            url = f"{self.base_url}/score/categorias-indicadores-pesos"
            
            print("Listando configuração completa...")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['status'] == 'OK':
                    dados = result['conteudo']
                    print(f"{len(dados)} configurações encontradas:")
                    for item in dados:
                        print(f"   - Categoria: {item['dsCategoria']} | Indicador: {item['dsIndicador']} | Peso: {item['pcPeso']}%")
                    return dados
                else:
                    print(f"Erro: {result['mensagem']}")
                    return []
            else:
                print(f"Erro HTTP: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            return []


def exemplo_completo():
    """
    Exemplo completo de uso da API
    """
    print("Iniciando exemplo completo da API de Score")
    print("=" * 60)
    
    # Criar cliente da API
    client = ScoreAPIClient()
    
    # 1. FAZER LOGIN
    print("\nETAPA: AUTENTICAÇÃO")
    if not client.login("api.registro.sac", "#api.R3g1str0.S@C!"):
        print("Falha na autenticação. Encerrando...")
        return
    
    # 2. CADASTRAR CATEGORIAS
    print("\nETAPA: CADASTRAR CATEGORIAS")
    cat1_id = client.cadastrar_categoria("Qualidade do Atendimento")
    cat2_id = client.cadastrar_categoria("Pontualidade na Entrega")
    cat3_id = client.cadastrar_categoria("Resolução de Problemas")
    
    # 3. CADASTRAR INDICADORES
    print("\nETAPA: CADASTRAR INDICADORES")  
    ind1_id = client.cadastrar_indicador("Tempo de Resposta")
    ind2_id = client.cadastrar_indicador("Satisfação do Cliente")
    ind3_id = client.cadastrar_indicador("Taxa de Resolução")
    
    # 4. CADASTRAR PESOS (se conseguiu criar categorias e indicadores)
    if all([cat1_id, cat2_id, cat3_id, ind1_id, ind2_id, ind3_id]):
        print("\nETAPA: CADASTRAR PESOS")
        client.cadastrar_peso(cat1_id, ind1_id, 30)  # Qualidade + Tempo = 30%
        client.cadastrar_peso(cat1_id, ind2_id, 25)  # Qualidade + Satisfação = 25%
        client.cadastrar_peso(cat2_id, ind3_id, 20)  # Pontualidade + Resolução = 20%
        client.cadastrar_peso(cat3_id, ind1_id, 25)  # Resolução + Tempo = 25%
    
    # 5. CADASTRAR SCORES DE CLIENTES
    print("\nETAPA: CADASTRAR SCORES")
    clientes_scores = [
        (16684, 8),
        (12345, 7),
        (98765, 9),
        (55555, 6)
    ]
    
    for cliente_id, score in clientes_scores:
        client.cadastrar_score(cliente_id, score)
    
    # 6. CONSULTAR SCORES
    print("\nETAPA: CONSULTAR SCORES")
    for cliente_id, _ in clientes_scores:
        client.consultar_score(cliente_id)
    
    # 7. LISTAR DADOS CADASTRADOS
    print("\nETAPA: LISTAR DADOS")
    client.listar_categorias()
    print()
    client.listar_indicadores()
    print()
    client.listar_categorias_indicadores_pesos()
    
    print("\nExemplo completo finalizado!")
    print("=" * 60)


def exemplo_simples():
    """
    Exemplo simples focado apenas em scores
    """
    print("Exemplo simples - apenas scores")
    print("=" * 40)
    
    client = ScoreAPIClient()
    
    # Login
    if client.login("seu_usuario", "sua_senha"):
        # Cadastrar alguns scores
        client.cadastrar_score(16684, 8)
        client.cadastrar_score(12345, 7)
        
        # Consultar os scores
        client.consultar_score(16684)
        client.consultar_score(12345)
    
    print("Exemplo simples finalizado!")


if __name__ == "__main__":
    print("CLIENTE PYTHON PARA API DE SCORE")
    print("Escolha o exemplo:")
    print("1 - Exemplo completo (todas as funcionalidades)")
    print("2 - Exemplo simples (apenas scores)")
    
    escolha = input("Digite sua escolha (1 ou 2): ").strip()
    
    if escolha == "1":
        exemplo_completo()
    elif escolha == "2":
        exemplo_simples()
    else:
        print("Opção inválida. Executando exemplo simples...")
        exemplo_simples()