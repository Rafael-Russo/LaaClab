# Material herdado ainda não convertido

Estes dois arquivos são template e script Django da tela **Explorar**, a única
das dez que não foi convertida na fase 1.

Ela ficou de fora porque depende de três coisas que a API ainda não tem: busca
sem acento, ordenação por pontuação (que mora em `bugometro_status` e exige
JOIN) e filtro por gênero. As três estão especificadas para a fase 2.

Não apague sem antes converter — o resto do material herdado já foi consumido
pelas nove telas de `view/paginas/`, e este é o que sobrou.
