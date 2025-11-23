# Aplicação simples de comunicação TCP

Programa cliente/servidor TCP simples para transferência de arquivos e chat.

## Protocolo
### Requisição (cliente):
O cliente solicita arquivos, recebe e valida hash, e troca mensagens de chat.

- `GET_FILE <filename>` — pede um arquivo ao servidor
- `CHAT <msg_len> <message>` — envia mensagem de chat
- `EXIT` — encerra o cliente

### Resposta (servidor):

O servidor aceita múltiplos clientes, responde a requisições `GET_FILE`, transmite arquivos com cabeçalho estruturado e envia mensagens de chat para todos os clientes conectados (ou algum em específico).
Formato do cabeçalho (no envio de arquivo)
- `status` (1 byte)
- `filename_len` (2 bytes, big-endian)
- `filename` (utf-8)
- `file_size` (8 bytes, big-endian)
- `hash_len` (2 bytes, big-endian)
- `hash` (bytes)

## Multithreading
O servidor possui uma thread para mensagens de chat no console, outra para aceitar novos clientes, e uma para cada cliente conectado.
O cliente possui uma thread para envio de requests e outra para receber respostas do servidor.
Por meio de um sistema de shutdown cooperativo, threads e sockets são fechados corretamente quando o servidor ou cliente terminam.