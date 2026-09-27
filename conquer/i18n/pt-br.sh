# shellcheck shell=bash disable=SC2034,SC2154
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Textos do menu do jogador e do assistente de cadastro, em português do
# Brasil. Todo texto que faltar aqui aparece em inglês (en.sh). Veja
# README.md.

MSG[language]="Português (Brasil)"

# Menu do jogador (menu.sh)
MSG[menu_pause]="${dim}Pressione qualquer tecla para voltar ao menu...${reset}"
MSG[menu_too_small]="${yellow}${bold}Seu terminal é pequeno demais: %s${reset}"
MSG[menu_needs_size]="Conquer precisa de pelo menos %s colunas x %s linhas.
Aumente a janela do navegador ou diminua o zoom (Ctrl e -).

Pressione uma tecla para verificar de novo, ou 'c' para continuar assim."
MSG[menu_ready_count]="%s de %s nações"
MSG[menu_all_ready]="  ${green}${bold}Todas as nações estão prontas: o turno será atualizado agora.${reset}
  Volte em alguns minutos para o novo turno."
MSG[menu_ask_done]="  Suas ordens deste turno estão prontas? [s/N] "
MSG[menu_yes]="sSyY"
MSG[menu_marked]="  ${green}Ordens marcadas como prontas.${reset} Você pode mudá-las até a atualização."
MSG[menu_unmarked]="  Suas ordens ${bold}não estão mais marcadas como prontas${reset}."
MSG[menu_marked_turn]="  ${green}Suas ordens deste turno estão marcadas como prontas.${reset}"
MSG[menu_early_note]="  O turno é antecipado assim que todas as nações estiverem prontas."
MSG[menu_not_yet]="ainda não"
MSG[menu_no_nation]="${dim}ainda sem nação atribuída${reset}"
MSG[menu_any_nation]="${dim}qualquer nação${reset}"
MSG[menu_nation]="nação ${bold}%s${reset}"
MSG[menu_signed_in]="  ${dim}Conectado como:  ${reset} ${bold}%s${reset} (%s)"
MSG[menu_last_update]="  ${dim}Último turno:    ${reset} %s"
MSG[menu_schedule]="  ${dim}Calendário:      ${reset} %s"
MSG[menu_schedule_unknown]="consulte o administrador"
MSG[menu_next_update]="  ${dim}Próximo turno:   ${reset} %s"
MSG[menu_date_format]="+%d/%m %H:%M %Z"
MSG[menu_orders_done]="  ${dim}Ordens prontas:  ${reset} %s"
MSG[menu_yours_done]="${green}(as suas: sim)${reset}"
MSG[menu_yours_not_yet]="${yellow}(as suas: ainda não)${reset}"
MSG[menu_updating]="  ${yellow}${bold}O turno está sendo atualizado.${reset} Volte em alguns minutos."
MSG[menu_update_failed]="  ${yellow}${bold}A última atualização do turno falhou${reset} (%s): ${dim}%s${reset}
  O administrador já foi avisado; suas ordens ficam guardadas para a
  próxima atualização."
MSG[menu_how_to_join]="${bold}Como participar da partida${reset}

Durante a fase de testes, as nações novas são criadas pelo administrador.

  1. Peça uma nação ao administrador. Você vai receber:
       - uma conta de jogador deste site, vinculada à sua nação
       - a senha da sua nação
  2. Entre com sua conta de jogador e escolha \"Jogar\" neste menu.
  3. Sua nação se abre direto: digite a senha da nação.

${bold}Como funcionam os turnos${reset}

Conquer é jogado em turnos. Você pode entrar quantas vezes quiser para dar
ordens (mover exércitos, recrutar, construir, fazer comércio...). Todas as
ordens são resolvidas juntas na próxima atualização do turno:
%s.

A atualização espera enquanto houver jogadores conectados, então saia do
jogo (tecla 'q') quando terminar. Ao sair, o menu pergunta se suas ordens
estão prontas; você também pode mudar isso com a opção 6.

As telas do jogo estão em inglês, como em 1987; o tutorial em português
do site explica cada uma."
MSG[menu_how_early]="Quando todas as nações marcam suas ordens como prontas, o turno é
atualizado na hora, sem esperar o calendário."
MSG[menu_admin_contact]="Contato do administrador: ${bold}%s${reset}"
MSG[menu_keys]="${bold}Teclas principais${reset}   (pressione '?' dentro do jogo para a ajuda completa)

  Movimento     y k u         Mapa e informações
                 \\|/           d   mudar visualização  s   pontuação
               h -+- l         N   ler o jornal        R   ler mensagens
                 /|\\           I   info da campanha    a   exércitos
                b j n         (o teclado numérico 1-9 também move)

  Ações         m   mover a unidade       D   recrutar tropas
                p   próxima unidade       C   construir
                r   mudar uso do setor    B   orçamento
                S   diplomacia            M   magia
                P   produção              q   sair

  Ctrl-L redesenha a tela se ela ficar bagunçada."
MSG[menu_practice_failed]="  ${yellow}Não foi possível criar seu mundo de treino.${reset}"
MSG[menu_practice_title]="  ${bold}${green}Mundo de treino${reset}   ${dim}só você joga aqui; nada conta${reset}"
MSG[menu_practice_nation]="  ${dim}Sua nação:    ${reset} ${bold}%s${reset}   ${dim}senha:${reset} ${bold}%s${reset}"
MSG[menu_practice_now]="  ${dim}Agora:        ${reset} %s"
MSG[menu_practice_intro]="  Teste o que quiser, rode você mesmo o próximo turno e veja o que acontece.
  O botão Coach, acima do jogo, guia você por um primeiro turno."
MSG[menu_practice_play]="Jogar com a nação de treino"
MSG[menu_practice_turn]="Rodar o próximo turno agora"
MSG[menu_practice_reset]="Recomeçar com um mundo novo"
MSG[menu_back]="Voltar ao menu principal"
MSG[menu_choose]="  Escolha uma opção: "
MSG[menu_practice_running]="  Rodando a atualização do turno do seu mundo de treino..."
MSG[menu_practice_done]="  ${green}Pronto:${reset} %s -> %s
  Jogue de novo para ler o jornal (N) e seu correio (R)."
MSG[menu_practice_not_run]="  ${yellow}A atualização não rodou.${reset} Saia antes do jogo de treino."
MSG[menu_practice_ask_reset]="  Apagar seu mundo de treino e começar de novo? [s/N] "
MSG[menu_practice_ready]="  ${green}Um novo mundo de treino está pronto.${reset}"
MSG[menu_scores_prompt]="Pontuação - q para voltar"
MSG[menu_updating_try_later]="  ${yellow}O turno está sendo atualizado.${reset} Tente de novo em alguns minutos."
MSG[menu_unassigned]="  ${yellow}Sua conta%s ainda não tem nação atribuída.${reset}
  Peça uma ao administrador (veja \"Como participar\" no menu)."
MSG[menu_opening]="Abrindo sua nação ${bold}%s${reset}."
MSG[menu_disconnected]="${yellow}Você foi desconectado para a atualização do turno.${reset}
Suas ordens foram salvas. Volte em alguns minutos para o novo turno."
MSG[menu_cannot_enter]="${yellow}Não foi possível entrar no jogo.${reset}
Confira o nome e a senha da sua nação. Se o turno estiver
sendo atualizado, tente de novo em alguns minutos."
MSG[menu_play]="Jogar"
MSG[menu_join]="Como participar / como funcionam os turnos"
MSG[menu_key_reference]="Teclas principais"
MSG[menu_scores]="Pontuação"
MSG[menu_help]="Ajuda completa (telas de ajuda do jogo, em inglês)"
MSG[menu_not_done]="Minhas ordens ainda não estão prontas"
MSG[menu_done]="Minhas ordens deste turno estão prontas"
MSG[menu_practice]="Mundo de treino (só você, nada conta)"
MSG[menu_log_out]="Sair"
MSG[menu_goodbye]="Até logo, comandante."

# Assistente de cadastro (join.sh)
MSG[join_questions]="Dúvidas: ${bold}%s${reset}"
MSG[join_again]="  Pressione qualquer tecla para começar de novo..."
MSG[join_title]="${bold}${green}Entre no Conquer${reset}"
MSG[join_closed]="No momento, este servidor não está aceitando novos jogadores."
MSG[join_welcome]="Bem-vindo! Você precisa de um ${bold}código de convite${reset} do administrador do jogo."
MSG[join_code]="  Código de convite: "
MSG[join_bad_code]="Esse código de convite não é válido ou já foi usado."
MSG[join_too_late]="A partida está no turno %s: depois do turno 5, as nações novas são
  criadas pelo administrador. Seu código continua válido; peça a ele
  que adicione sua nação."
MSG[join_choose_account]="Escolha a ${bold}conta de jogador${reset} com que você vai entrar neste site
  ${dim}(letras, números, . _ - ; até 32 caracteres)${reset}"
MSG[join_account]="  Nome da conta: "
MSG[join_bad_account]="Use apenas letras, números, pontos, hifens e sublinhados."
MSG[join_account_exists]="A conta '%s' já existe. Escolha outro nome."
MSG[join_password]="  Senha (pelo menos 8 caracteres): "
MSG[join_password_again]="  Repita a senha: "
MSG[join_password_mismatch]="As senhas não conferem."
MSG[join_password_short]="Use pelo menos 8 caracteres."
MSG[join_builder]="
  ${bold}Agora crie sua nação${reset} com o criador de nações do jogo
  (as telas dele estão em inglês).

  Ele vai pedir:
    - um ${bold}nome de nação${reset} (até 9 letras) e uma ${bold}senha da nação${reset}
      (até 7 caracteres; o jogo pede essa senha sempre que você joga)
    - o nome do seu governante, uma ${bold}raça${reset}, uma ${bold}classe${reset} e um ${bold}alinhamento${reset}
    - uma marca no mapa: qualquer letra livre da lista
  Depois você distribui pontos na sua nação. Mova-se com ${bold}j${reset} e ${bold}k${reset},
  pressione ${bold}h${reset} para passar a adicionar e ${bold}Espaço${reset} para comprar.
  ${yellow}Dica:${reset} compre 2 ou 3 pontos de ${bold}Treasury${reset} (tesouro); uma nação sem
  ouro não consegue recrutar tropas no primeiro turno. ${bold}Esc${reset} termina (o
  resto vai para a população), depois responda ${bold}y${reset} para salvar.
"
MSG[join_open_builder]="  Pressione qualquer tecla para abrir o criador de nações..."
MSG[join_no_nation]="Nenhuma nação foi criada, então a conta também não.
  Seu código de convite continua válido."
MSG[join_code_used]="Esse código de convite foi usado nesse meio-tempo.
  Pergunte ao administrador sobre a nação %s."
MSG[join_not_saved]="Sua nação %s foi criada, mas não foi possível salvar a conta.
  Avise o administrador."
MSG[join_done]="
  ${bold}${green}Bem-vindo à partida, soberano de %s!${reset}

  Sua conta de jogador ${bold}%s${reset} está pronta.

  Para jogar, entre de novo com ela: feche esta aba (ou abra o site numa
  janela anônima), clique em ${bold}Jogar agora${reset} e use ${bold}%s${reset} e sua
  senha. Sua nação se abre direto; a senha dela é a que você definiu
  no criador de nações.

  Novo no Conquer? A opção 7 do menu é um mundo de treino, e o botão
  Coach guia você pelo seu primeiro turno.
"
MSG[join_finish]="  Pressione qualquer tecla para terminar..."
MSG[join_goodbye]="  Até logo, e nos vemos no mapa."
