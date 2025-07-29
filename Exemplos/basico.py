#!python3

def saudacao(nome = 'Pessoa', idade = 20):
    print(f'Bom dia {nome}! \nVc nem parece ter {idade} anos!')

#def saudacao():
#    print('Boa tarde!')

def soma_e_multiplicacao(a, b, x):
    return a + b * x 

if __name__ == '__main__':
    saudacao('Ana', idade = 30)

#print(__name__)