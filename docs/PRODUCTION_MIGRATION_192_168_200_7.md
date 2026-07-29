# Histórico da proposta de migração para 192.168.200.7

## Estado

Esta proposta foi **substituída em 2026-07-29** pela decisão de manter o endereço
`192.168.200.4` como entrada oficial e executar o runtime isolado em
`192.168.200.160`.

Nenhum runtime, Docker, WSL, banco ou aplicação do Vulcan foi instalado no
`192.168.200.7`. O host não é requisito do corte atual.

O inventário histórico permanece registrado no Git. O estado autoritativo, comandos,
backups, validações, limitações e rollback estão em:

`docs/PRODUCTION_ERS_192_168_200_4.md`

Arquitetura vigente:

```text
clientes/TV/agentes
        |
        v
192.168.200.4:8099  (somente portproxy/firewall)
        |
        v
192.168.200.160:8099  (edge + runtime Docker isolado)
```

O SRVERS01 continua dedicado a AD DS e DNS. Não remova o listener 8099 enquanto essa
arquitetura estiver vigente.
