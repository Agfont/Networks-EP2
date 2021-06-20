# MAC0352 - Redes de  Computadores e Sistemas Distribuídos
## EP2 - Sistema Distribuído (Jogo da Velha)
### Arthur Font Gouveia - 12036152
### Lucas Pires Stankus - 10723624
> Status: Finished

Este projeto implementa um sistema distribuído que possibilita partidas de jogo da velha em uma arquitetura híbrida (P2P e cliente/servidor) com tolerância a algumas falhas.\
Os clientes se comunicam com o servidor para algumas ações (cliente/servidor) e posteriormente conectam-se entre si para realizarem uma partida (P2P).\
O servidor registra alguns acontecimentos em um arquivo de log para permitir a reconstrução do estado do servidor caso ocorra alguma uma falha.

## O protocolo de rede desenvolvido atende aos seguintes requisitos:
+ Conexão de vários clientes simultaneamente
+ Envio criptografado das credenciais de usuário e senha
+ Heartbeat entre servidor e clientes
+ Verificação periódica entre clientes da latência entre eles durante uma partida
+ Troca de mensagens em modo texto (ASCII) entre cliente e servidor e entre clientes

## Informações registradas no log:
* Servidor iniciado
* Conexão realizada por um cliente (Endereço IP do cliente)
* Login com sucesso ou não (Nome do usuário que conseguiu, ou não, logar, e endereço IP de onde veio o login)
* Logout com sucesso
* Desconexão realizada por um cliente (Endereço IP do cliente)
* Desconexão inesperada de um cliente, verificada pelos heartbeats (Endereço IP do cliente)
* Início de uma partida (Endereço IP e nomes dos usuários dos jogadores)
* Finalização de uma partida (Endereço IP, nomes dos usuários dos jogadores e nome do vencedor)
* Servidor finalizado

## Comandos aceitos pelo sistema (via prompt do cliente):
* adduser <usuario> <senha>: cria um novo usuário
* passwd <senha antiga> <senha nova>: muda a senha do usuário
* login <usuario> <senha>: loga
* leaders: informa a tabela de pontuação de todos os usuários registrados no sistema
* list: lista todos os usuários conectados no momento e se estão ocupados em uma partida ou não
* begin <oponente>: convida um oponente para jogar. Ele pode aceitar ou não
* send <linha> <coluna>: envia a jogada
* delay: durante uma partida, informa os 3 últimos valores de latência que foram medidos para o
cliente do oponente
* end: encerra uma partida antes da hora
* logout: desloga
* exit: finaliza a execução do cliente e retorna para o shell do sistema operacional

## Tolerância a falhas
O sistema tolera as seguintes falhas do servidor, limitadas a um intervalo de 3 minutos.
* Processo do servidor foi finalizado por um ‘kill -9‘
* Rede do servidor foi desconectada por um ‘ifdown‘

## Tecnologias Utilizadas:

<table>
  <tr>
    <td>Python</td>
    <td>Pandas</td>
    <td>OpenSSL</td>
    <td>Wireshark</td>
  </tr>
  <tr>
    <td>3.8.5</td>
    <td>1.2.3</td>
    <td>1.1.1k</td>
    <td>3.2.3</td>
  </tr>
</table>

Para instalar o pandas, basta executar o seguinte comando no shell:
```
$ pip install pandas
```
## Compilação, Remoção e Inicialização:
Para a criptografia do servidor funcionar corretamente são necessárias uma chave pública (pk) e uma secreta (sk), para gerar ambas use o seguinte comando dentro do diretório `/perm`:
```
$ openssl req -new -x509 -days 365 -nodes -out pk.pem -keyout sk.pem -subj "/CN=JogoDaVelha"
```
Para incializar o servidor, basta executar o seguinte comando no shell:
```
$ python3 main.py <PORT>
```
O programa recebe como argumento a porta em que desejamos que o servidor trabalhe.\

## Testes:
Uma vez inicializado o servidor, para verificar sua correta execução, foram utilizados máquinas virtuais para simular os clientes em outras máquinas.

Em cada máquina virtual, foi executado o seguinte comando:

```
$ python3 main.py <IP Adress> <PORT>
```
Onde:
+ **IP Adress**: campo destinado ao endereço IP do servidor
+ **PORT**: campo destinado a porta do servidor
