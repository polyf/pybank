from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, render_template, request, send_file
from flask_cors import CORS
from sqlalchemy import func
import tempfile

from flask import Flask, render_template

app = Flask(__name__, static_folder='', static_url_path='/')

CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
db = SQLAlchemy(app)

app.config['TEMPLATE_FOLDER'] = 'templates'

# Definir os modelos
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    sexo = db.Column(db.String(10), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    conta = db.relationship('ContaBancaria', backref='cliente', uselist=False)
    
    def serialize(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'sexo': self.sexo,
            'cpf': self.cpf,
            'data_nascimento': self.data_nascimento.strftime('%Y-%m-%d')
        }

class TipoConta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    contas = db.relationship('ContaBancaria', backref='tipo_conta', lazy=True)

class ContaBancaria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    tipo_conta_id = db.Column(db.Integer, db.ForeignKey('tipo_conta.id'), nullable=False)
    saldo_inicial = db.Column(db.Float, nullable=False)
    movimentacoes = db.relationship('Movimentacao', backref='conta', lazy=True)

class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Integer, nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey('conta_bancaria.id'), nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=datetime.now())
    valor = db.Column(db.Float, nullable=False)

# Implementação dos Endpoints

#################### CLIENTES ##############################

# Adiciona um novo cliente
@app.route('/clientes', methods=['POST'])
def cadastrar_cliente():
    data = request.get_json()
    novo_cliente = Cliente(
        nome=data['nome'],
        sexo=data['sexo'],
        cpf=data['cpf'],
        data_nascimento=datetime.strptime(data['data_nascimento'], '%Y-%m-%d')
    )

    try:
        db.session.add(novo_cliente)
        db.session.commit()
        return jsonify({"message": "Cliente cadastrado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao cadastrar cliente.", "error": str(e)}), 500
    
# Método para obter todos os clientes
@app.route('/clientes', methods=['GET'])
def getClientes():
    clientes = Cliente.query.all()
    clientes_serializados = [cliente.serialize() for cliente in clientes]
    return jsonify(clientes_serializados)

    
# Método para obter um cliente pelo ID
@app.route('/clientes/<int:cliente_id>', methods=['GET'])
def getCliente(cliente_id):
    cliente = Cliente.query.get(cliente_id)
    if cliente is None:
        return jsonify({"message": "Cliente não encontrado"}), 404
    return jsonify(cliente.serialize())

# Método para editar um cliente pelo ID
@app.route('/clientes/<int:cliente_id>', methods=['PUT'])
def editCliente(cliente_id):
    cliente = Cliente.query.get(cliente_id)
    if cliente is None:
        return jsonify({"message": "Cliente não encontrado"}), 404

    data = request.get_json()
    cliente.nome = data['nome']
    cliente.sexo = data['sexo']
    cliente.cpf = data['cpf']
    cliente.data_nascimento = datetime.strptime(data['data_nascimento'], '%Y-%m-%d')

    try:
        db.session.commit()
        return jsonify({"message": "Cliente editado com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao editar cliente.", "error": str(e)}), 500

# Método para excluir um cliente pelo ID
@app.route('/clientes/<int:cliente_id>', methods=['DELETE'])
def deleteCliente(cliente_id):
    cliente = Cliente.query.get(cliente_id)
    if cliente is None:
        return jsonify({"message": "Cliente não encontrado"}), 404

    try:
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({"message": "Cliente excluído com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao excluir cliente.", "error": str(e)}), 500


#################### CONTAS ##############################

# Adiciona uma nova conta
@app.route('/contas', methods=['POST'])
def abrir_conta():
    data = request.get_json()
    cpf = data['cpf']
    tipo_conta_id = int(data['tipo_conta'])
    saldo_inicial = float(data['saldo_inicial'])

    cliente = Cliente.query.filter_by(cpf=cpf).first()
    tipo_conta = TipoConta.query.get(tipo_conta_id)

    if not cliente:
        return jsonify({"message": "Cliente não encontrado."}), 404
    if cliente.conta:
        return jsonify({"message": "O cliente já possui uma conta."}), 400
    if not tipo_conta:
        return jsonify({"message": "Tipo de conta inválido."}), 400

    nova_conta = ContaBancaria(cliente=cliente, tipo_conta=tipo_conta, saldo_inicial=saldo_inicial)

    try:
        db.session.add(nova_conta)
        db.session.commit()
        return jsonify({"message": "Conta criada com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao criar conta.", "error": str(e)}), 500

# Adiciona um tipo de conta
@app.route('/tipos-conta', methods=['POST'])
def adicionar_tipo_conta():
    data = request.get_json()
    tipo = data.get('tipo')

    if not tipo:
        return jsonify({"message": "O campo 'tipo' é obrigatório."}), 400

    novo_tipo_conta = TipoConta(tipo=tipo)

    try:
        db.session.add(novo_tipo_conta)
        db.session.commit()
        return jsonify({"message": "Tipo de conta adicionado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao adicionar tipo de conta.", "error": str(e)}), 500
    
# Endpoint para listar todos os tipos de conta
@app.route('/tipos-conta', methods=['GET'])
def listar_tipos_conta():
    tipos_conta = TipoConta.query.all()
    tipos_conta_json = [{"id": tipo.id, "tipo": tipo.tipo} for tipo in tipos_conta]
    return jsonify(tipos_conta_json)

# Endpoint para atualizar um tipo de conta existente
@app.route('/tipos-conta/<int:id>', methods=['PUT'])
def atualizar_tipo_conta(id):
    tipo_conta = TipoConta.query.get(id)
    if not tipo_conta:
        return jsonify({"message": "Tipo de conta não encontrado."}), 404

    data = request.get_json()
    tipo = data.get('tipo')

    if not tipo:
        return jsonify({"message": "O campo 'tipo' é obrigatório."}), 400

    tipo_conta.tipo = tipo

    try:
        db.session.commit()
        return jsonify({"message": "Tipo de conta atualizado com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao atualizar tipo de conta.", "error": str(e)}), 500

# Endpoint para excluir um tipo de conta existente
@app.route('/tipos-conta/<int:id>', methods=['DELETE'])
def excluir_tipo_conta(id):
    tipo_conta = TipoConta.query.get(id)
    if not tipo_conta:
        return jsonify({"message": "Tipo de conta não encontrado."}), 404

    try:
        db.session.delete(tipo_conta)
        db.session.commit()
        return jsonify({"message": "Tipo de conta excluído com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Erro ao excluir tipo de conta.", "error": str(e)}), 500
    
api_url = "http://127.0.0.1:5000"

@app.route('/')
def index():
    mensagem_erro = request.args.get('mensagem_erro', '')
    return render_template('index.html', api_url=api_url, mensagem_erro=mensagem_erro)

# Esta parte assume que você já possui as definições das classes Cliente e ContaBancaria

@app.route('/login', methods=['POST'])
def login():
    nome = request.form['nome']
    cpf = request.form['cpf']

    # Verifica se o cliente existe no banco de dados
    cliente = Cliente.query.filter_by(nome=nome, cpf=cpf).first()

    if cliente:
        # Cliente existe
        if cliente.conta:
            # Cliente possui uma conta
            conta = cliente.conta
            cpf_cliente = cliente.cpf
            saldo_conta = conta.saldo_inicial
            tipo_conta = conta.tipo_conta.tipo

            # Renderiza o HTML com os dados da conta
            return render_template('home.html', cpf=cpf_cliente, saldo=saldo_conta, tipo=tipo_conta)
        else:
            # Cliente não possui uma conta, renderiza o HTML sem dados da conta
            return render_template('home.html', cpf=cpf)
    else:
        # Cliente não existe, envia mensagem de erro
        return render_template('index.html', erro="Cliente não encontrado, por favor, verifique seus dados.")

@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

@app.route('/criar-cliente', methods=['POST'])
def criarCliente():
    nome = request.form['nome']
    cpf = request.form['cpf']
    data_nascimento = request.form['dataNascimento']  # Corrigido para 'dataNascimento'
    sexo = request.form['sexo']

    cliente = Cliente.query.filter_by(cpf=cpf).first()

    if cliente:
        return render_template('cadastro.html', erro="Cliente já cadastrado.")
    else:
        # Converta a data de nascimento para o formato datetime
        data_nascimento = datetime.strptime(data_nascimento, '%Y-%m-%d')
        
        # Corrija a formatação, adicione uma vírgula após data_nascimento
        novo_cliente = Cliente(nome=nome, cpf=cpf, data_nascimento=data_nascimento, sexo=sexo)

        try:
            db.session.add(novo_cliente)
            db.session.commit()
            return render_template('index.html', sucesso="Cliente cadastrado com sucesso!")
        except Exception as e:
            db.session.rollback()
            return render_template('cadastro.html', erro="Erro ao cadastrar cliente.")

@app.route('/nova-conta', methods=['POST'])
def novaConta():
    cpf = request.form['cpf']
    return render_template('nova-conta.html', cpf=cpf)

@app.route('/criar-conta', methods=['POST'])
def criarConta():
    cpf = request.form['cpf']
    cliente = Cliente.query.filter_by(cpf=cpf).first()
    id_cliente = cliente.id
    tipo_conta = request.form['tipoConta']
    saldo_inicial = 0.0

    nova_conta = ContaBancaria(cliente_id=id_cliente, tipo_conta_id=int(tipo_conta), saldo_inicial=saldo_inicial)

    try:
        db.session.add(nova_conta)
        db.session.commit()
        tipo_conta = TipoConta.query.get(int(tipo_conta)).tipo
        return render_template('home.html', cpf=cpf, saldo=saldo_inicial, tipo=tipo_conta)
    except Exception as e:
            db.session.rollback()
            return render_template('home.html', erro="Erro ao cadastrar conta.")
    
@app.route('/conta', methods=['GET'])
def conta():
    cpf = request.args.get('cpf')
    cliente = Cliente.query.filter_by(cpf=cpf).first()
    transacoes = cliente.conta.movimentacoes
    return render_template('conta.html', conta=cliente.conta.id, transacoes=transacoes, tipo_conta = cliente.conta.tipo_conta_id)

@app.route('/saque')
def sacar():
    conta = request.args.get('conta')
    return render_template('saque.html', conta=conta)

@app.route('/deposito')
def depositar():
    conta = request.args.get('conta')
    return render_template('deposito.html', conta=conta)

@app.route('/juros')
def juros():
    conta = request.args.get('conta')
    return render_template('juros.html', conta=conta)

@app.route('/relatorio')
def relatorio():
    conta = request.args.get('conta')
    return render_template('relatorio.html', conta=conta)

@app.route('/realizar-saque', methods=['POST'])
def realizar_saque():
    conta = request.form['conta']
    valor = float(request.form['valor'])

    # Verifica se o valor do saque é válido (maior que zero)
    if valor <= 0:
        return render_template('saque.html', erro="O valor do saque deve ser maior que zero.")

    # Verifique se a conta existe (substitua 'ContaBancaria' pelo nome correto da sua classe de conta)
    conta_bancaria = ContaBancaria.query.get(conta)
    
    if not conta_bancaria:
        return render_template('saque.html', erro="Conta não encontrada.")
    
    # Verifique se o saldo é suficiente para o saque
    if conta_bancaria.saldo_inicial < valor:
        return render_template('saque.html', erro="Saldo insuficiente.", conta=conta_bancaria.id)

    # Crie uma nova movimentação de saque
    movimentacao = Movimentacao(tipo=2, conta=conta_bancaria, valor=valor)

    try:
        # Atualize o saldo da conta após o saque
        conta_bancaria.saldo_inicial -= valor
        
        # Salve a movimentação e o saldo atualizado no banco de dados
        db.session.add(movimentacao)
        db.session.commit()

        return render_template('home.html', sucesso="Operação realizada com sucesso!", cpf=conta_bancaria.cliente.cpf, saldo=conta_bancaria.saldo_inicial, tipo=conta_bancaria.tipo_conta.tipo)
    except Exception as e:
        db.session.rollback()
        return render_template('saque.html', erro="Erro ao realizar saque.")

@app.route('/realizar-deposito', methods=['POST'])
def realizar_deposito():
    conta = request.form['conta']
    valor = float(request.form['valor'])

    # Verifica se o valor do depósito é válido (maior que zero)
    if valor <= 0:
        erro = "O valor do depósito deve ser maior que zero."
        return render_template('deposito.html', erro=erro, conta=conta)

    # Verifique se a conta existe (substitua 'ContaBancaria' pelo nome correto da sua classe de conta)
    conta_bancaria = ContaBancaria.query.get(conta)
    
    if not conta_bancaria:
        erro = "Conta não encontrada."
        return render_template('deposito.html', erro=erro, conta=conta)

    # Crie uma nova movimentação de depósito
    movimentacao = Movimentacao(tipo=1, conta=conta_bancaria, valor=valor)

    try:
        # Atualize o saldo da conta após o depósito
        conta_bancaria.saldo_inicial += valor
        
        # Salve a movimentação e o saldo atualizado no banco de dados
        db.session.add(movimentacao)
        db.session.commit()

        # Redirecione para a página de sucesso ou outra página após o depósito
        return render_template('home.html', sucesso="Operação realizada com sucesso!", cpf=conta_bancaria.cliente.cpf, saldo=conta_bancaria.saldo_inicial, tipo=conta_bancaria.tipo_conta.tipo)
    except Exception as e:
        db.session.rollback()
        erro = "Erro ao realizar depósito. Detalhes: " + str(e)
        return render_template('saque.html', erro="Erro ao realizar depósito.")

# Rota para realizar a aplicação de juros
@app.route('/aplicar-juros', methods=['POST'])
def realizar_aplicacao_juros():
    conta = request.form['conta']
    taxa_juros = float(request.form['taxa'])

    # Verifique se a taxa de juros é válida (maior que zero)
    if taxa_juros <= 0:
        erro = "A taxa de juros deve ser maior que zero."
        return render_template('juros.html', erro=erro, conta=conta)

    # Verifique se a conta existe (substitua 'ContaBancaria' pelo nome correto da sua classe de conta)
    conta_bancaria = ContaBancaria.query.get(conta)
    
    if not conta_bancaria:
        erro = "Conta não encontrada."
        return render_template('juros.html', erro=erro, conta=conta)

    # Verifique se o tipo de conta é poupança ou investimento (substitua 'TipoConta' pelo nome correto da sua classe de tipo de conta)
    if conta_bancaria.tipo_conta_id not in [2, 3]:
        erro = "A operação de aplicação de juros está disponível apenas para contas de poupança e investimento."
        return render_template('juros.html', erro=erro, conta=conta)

    # Crie uma nova movimentação de aplicação de juros (tipo 3)
    movimentacao = Movimentacao(tipo=3, conta=conta_bancaria, valor=0)  # Valor zero, pois a movimentação representa apenas a aplicação de juros

    try:
        # Calcule o valor dos juros com base na taxa e no saldo atual da conta
        valor_juros = conta_bancaria.saldo_inicial * (taxa_juros / 100)
        
        # Atualize o saldo da conta após a aplicação de juros
        conta_bancaria.saldo_inicial += valor_juros
        
        # Atualize o valor da movimentação com o valor dos juros
        movimentacao.valor = valor_juros
        
        # Salve a movimentação e o saldo atualizado no banco de dados
        db.session.add(movimentacao)
        db.session.commit()

        # Redirecione para a página de sucesso ou outra página após a aplicação de juros
        return render_template('home.html', sucesso="Operação realizada com sucesso!", cpf=conta_bancaria.cliente.cpf, saldo=conta_bancaria.saldo_inicial, tipo=conta_bancaria.tipo_conta.tipo)
    except Exception as e:
        db.session.rollback()
        erro = "Erro ao aplicar juros. Detalhes: " + str(e)
        return render_template('juros.html', erro=erro, conta=conta)
    
@app.route('/gerar_relatorio', methods=['POST'])
def gerar_relatorio():
    conta = request.form['conta']
    data_inicio = request.form['dataInicio']
    data_fim = request.form['dataFim']
    conta_bancaria = ContaBancaria.query.filter_by(id=conta).first()
    
    try:
        data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')

        if data_inicio_obj > data_fim_obj:
            return render_template('relatorio.html', erro="A data inicial deve ser menor que a data final.", conta=conta)
    except ValueError:
        return render_template('relatorio.html', erro="Formato de data inválido.", conta=conta)


    cliente = Cliente.query.get(conta_bancaria.cliente_id)


    # Cabecalho do relatório
    relatorio = f"Relatório de Movimentações\n\n"
    relatorio += f"Dados do Cliente:\n"
    relatorio += f"Nome do Cliente: {cliente.nome}\n"
    relatorio += f"CPF: {cliente.cpf}\n\n"
    
    if (conta_bancaria.tipo_conta_id == 1):
        conta_bancaria_tipo = "Conta Corrente"
    elif (conta_bancaria.tipo_conta_id == 2):
        conta_bancaria_tipo = "Conta Poupança"
    elif (conta_bancaria.tipo_conta_id == 3):
        conta_bancaria_tipo = "Conta Investimento"
    else:
        conta_bancaria_tipo = "Desconhecida"

    relatorio += f"Dados da Conta Bancária:\n"
    relatorio += f"Tipo de Conta: {conta_bancaria_tipo}\n"
    relatorio += f"Número da Conta: {conta_bancaria.id}\n\n"


    relatorio += f"Informações do Relatório:\n"
    relatorio += f"Data Inicial: {data_inicio}\n"
    relatorio += f"Data Final: {data_fim}\n\n"
    
    # Movimentacoes do relatorio

    data_inicio_filtro = datetime.strptime(data_inicio, '%Y-%m-%d')
    data_fim_filtro = datetime.strptime(data_fim, '%Y-%m-%d')

    movimentacoes = ( Movimentacao.query.filter_by(conta_id=conta)
    .filter(Movimentacao.data >= data_inicio_filtro, Movimentacao.data <= data_fim_filtro).all())

    relatorio += f"Listagem das Movimentações:\n"
    contador = 1
    for item in movimentacoes:
        tipo_item = ""
        data_formatada = item.data.strftime("%m/%d/%Y %H:%M:%S %f")[:-3]  # Formata a data
        if (item.tipo == 1):
            tipo_item = "Depósito"
        elif (item.tipo == 2):
            tipo_item = "Saque"
        elif (item.tipo == 3):
            tipo_item = "Juros"
        relatorio += f"{contador}. Data: {data_formatada}, Tipo: {tipo_item}, Valor: R$ {item.valor}\n"
        contador += 1
    relatorio += f"\n"

    # Rodape do relatorio

    query_depositos = db.session.query(
        func.count(Movimentacao.id).label("quantidade"),
        func.sum(Movimentacao.valor).label("total_valor")
    ).filter(
        Movimentacao.tipo == 1,  # Supondo que 1 representa depósitos
        Movimentacao.conta_id == conta
    ).first()

    quantidade_depositos = query_depositos.quantidade
    total_valor_depositos = query_depositos.total_valor

    query_saques = db.session.query(
        func.count(Movimentacao.id).label("quantidade"),
        func.sum(Movimentacao.valor).label("total_valor")
    ).filter(
        Movimentacao.tipo == 2,  # Supondo que 2 representa saques
        Movimentacao.conta_id == conta
    ).first()

    quantidade_saques = query_saques.quantidade
    total_valor_saques = query_saques.total_valor

    query_juros = db.session.query(
        func.count(Movimentacao.id).label("quantidade"),
        func.sum(Movimentacao.valor).label("total_valor")
    ).filter(
        Movimentacao.tipo == 3,  # Supondo que 3 representa operações de juros
        Movimentacao.conta_id == conta
    ).first()

    quantidade_juros = query_juros.quantidade
    total_valor_juros = query_juros.total_valor

    relatorio += f"Estatísticas da conta:\n"
    relatorio += f"Quantidade e valor dos depósitos realizados: {quantidade_depositos} depósito(s), R$ {total_valor_depositos}\n"
    relatorio += f"Quantidade e valor dos saques realizados: {quantidade_saques} saque(s), R$ {total_valor_saques}\n"

    print(conta_bancaria.tipo_conta_id)
    if (conta_bancaria.tipo_conta_id in [2, 3]):
        relatorio += f"Quantidade e valor das operações de juros aplicados: {quantidade_juros} operação(ões) de juros, R$ {total_valor_juros}\n\n"


    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as arquivo_temporario:
        nome_arquivo = arquivo_temporario.name
        arquivo_temporario.write(relatorio.encode('utf-8'))

    # Envia o arquivo como um download
    return send_file(
        nome_arquivo,
        as_attachment=True,
        download_name='relatorio' + cliente.nome + data_inicio + '-' + data_fim + '.txt',
        mimetype='text/plain'
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)