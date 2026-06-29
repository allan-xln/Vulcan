# ERS Admin

O tenant local de piloto ERS usa o UUID `00000000-0000-0000-0000-000000000301`, o mesmo lido pelo frontend de demo.

## Garantir usuário ERS

Não grave senha em arquivo versionado. Para criar ou atualizar o usuário administrativo ERS:

```bash
cd /home/allan/Dev/Vulcan
DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55432/vulcan' \
ERS_INITIAL_PASSWORD='defina-em-runtime' \
.venv/bin/python scripts/ensure_ers_admin.py
```

O script é idempotente e garante:

- tenant exibido como `ERS Transportes`;
- perfil `ERS` com escopo `tenant`;
- departamento raiz `ERS`;
- usuário/login `ERS`;
- senha armazenada via `crypt`, nunca em texto puro;
- metadados `passwordTemporary=true`;
- membership raiz nível `0`;
- refresh de `membership_closure`;
- audit logs com senha mascarada.

## Permissão

O perfil `ERS` tem escopo `tenant`, portanto vê e administra todo o tenant ERS: usuários, equipes, dispositivos, métricas, insights, notificações, configurações e adoção. O root global continua acima do tenant e segue reservado para operação da plataforma.

## Validação rápida

```bash
curl -fsS -X POST http://192.168.200.4:3001/auth/login \
  -H 'Content-Type: application/json' \
  --data '{"username":"ERS","password":"senha-runtime"}'
```

Após login, o aviso deve indicar senha temporária. A troca forçada em primeiro login ainda depende da tela dedicada de troca de senha.
