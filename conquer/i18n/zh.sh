# shellcheck shell=bash disable=SC2034,SC2154,SC1111
# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later
#
# 玩家菜单和加入向导的文字（简体中文）。此处缺少的文字会以英文显示
# （en.sh）。参见 README.md。

MSG[language]="简体中文"

# 玩家菜单 (menu.sh)
MSG[menu_pause]="${dim}按任意键返回菜单...${reset}"
MSG[menu_too_small]="${yellow}${bold}你的终端窗口太小：%s${reset}"
MSG[menu_needs_size]="Conquer 至少需要 %s 列 x %s 行。
请把浏览器窗口调大，或缩小页面（Ctrl 加 -）。

按任意键重新检测，或按 'c' 仍然继续。"
MSG[menu_ready_count]="%s / %s 个国家"
MSG[menu_all_ready]="  ${green}${bold}所有国家都已就绪：回合结算现在开始。${reset}
  几分钟后再回来，迎接新的回合。"
MSG[menu_ask_done]="  本回合的指令下达完了吗？[y/N] "
MSG[menu_yes]="yY"
MSG[menu_marked]="  ${green}指令已标记为完成。${reset}回合结算之前仍可修改。"
MSG[menu_unmarked]="  你的指令${bold}已不再标记为完成${reset}。"
MSG[menu_marked_turn]="  ${green}你本回合的指令已标记为完成。${reset}"
MSG[menu_early_note]="  所有国家都完成后，回合结算会提前进行。"
MSG[menu_not_yet]="尚未完成"
MSG[menu_no_nation]="${dim}尚未分配国家${reset}"
MSG[menu_any_nation]="${dim}任意国家${reset}"
MSG[menu_nation]="国家 ${bold}%s${reset}"
MSG[menu_signed_in]="  ${dim}登录身份：    ${reset} ${bold}%s${reset}（%s）"
MSG[menu_last_update]="  ${dim}上次回合结算：${reset} %s"
MSG[menu_schedule]="  ${dim}回合时间表：  ${reset} %s"
MSG[menu_schedule_unknown]="请询问游戏管理员"
MSG[menu_next_update]="  ${dim}下次回合结算：${reset} %s"
MSG[menu_date_format]="+%m月%d日 %H:%M %Z"
MSG[menu_orders_done]="  ${dim}指令已完成：  ${reset} %s"
MSG[menu_yours_done]="${green}（你：已完成）${reset}"
MSG[menu_yours_not_yet]="${yellow}（你：尚未完成）${reset}"
MSG[menu_updating]="  ${yellow}${bold}回合结算正在进行中。${reset}请几分钟后再回来。"
MSG[menu_update_failed]="  ${yellow}${bold}上次回合结算失败${reset}（%s）：${dim}%s${reset}
  已通知管理员；你的指令会保留到下一次结算。"
MSG[menu_how_to_join]="${bold}如何加入游戏${reset}

加入需要邀请。

  1. 向游戏管理员索取邀请码。
  2. 在主页选择\"创建账号\"，输入邀请码，并设置账号名和密码。
  3. 用这个账号登录并选择\"游戏\"：游戏会让你建立国家，
     之后会直接打开它。

${bold}回合如何进行${reset}

Conquer 以回合制进行。你可以随时登录、随意多次下达指令（调动军队、
征兵、建造、贸易……）。所有指令会在下一次回合结算时统一执行：
%s。

有玩家在线时回合结算会等待，所以完成后请退出游戏（按 'q'）。
退出时，菜单会询问你的指令是否已完成；你也可以用选项 6 修改。

游戏画面保持 1987 年的英文原貌；网站上的中文教程会逐一讲解。"
MSG[menu_how_early]="当所有国家都把指令标记为完成时，回合结算会立即进行，
不必等到预定时间。"
MSG[menu_admin_contact]="管理员联系方式：${bold}%s${reset}"
MSG[menu_keys]="${bold}快捷键一览${reset}   （在游戏中按 '?' 查看完整帮助）

  移动          y k u         地图与信息
                 \\|/           d   切换显示            s   分数
               h -+- l         N   阅读报纸            R   阅读消息
                 /|\\           I   战役信息            a   军队报告
                b j n         （数字小键盘 1-9 也可移动）

  行动          m   移动所选单位          D   征兵
                p   选择下一单位          C   建造
                r   改变地块用途          B   预算
                S   外交                  M   魔法
                P   生产                  q   退出

  如果画面错乱，按 Ctrl-L 重绘屏幕。"
MSG[menu_practice_failed]="  ${yellow}无法创建你的练习世界。${reset}"
MSG[menu_practice_title]="  ${bold}${green}练习世界${reset}   ${dim}只有你一个人玩，一切都不计入成绩${reset}"
MSG[menu_practice_nation]="  ${dim}你的国家：${reset} ${bold}%s${reset}   ${dim}密码：${reset}${bold}%s${reset}"
MSG[menu_practice_now]="  ${dim}当前：    ${reset} %s"
MSG[menu_practice_intro]="  随便尝试，自己推进下一回合，看看会发生什么。
  游戏上方的 Coach（教练）按钮会一步步带你走完第一个回合。"
MSG[menu_practice_play]="用练习国家进行游戏"
MSG[menu_practice_turn]="立即推进下一回合"
MSG[menu_practice_reset]="换一个新世界重新开始"
MSG[menu_back]="返回主菜单"
MSG[menu_choose]="  请选择："
MSG[menu_practice_running]="  正在进行练习世界的回合结算..."
MSG[menu_practice_done]="  ${green}完成：${reset}%s -> %s
  再次进入游戏，阅读报纸（N）和你的邮件（R）。"
MSG[menu_practice_not_run]="  ${yellow}回合结算没有进行。${reset}请先退出练习游戏。"
MSG[menu_practice_ask_reset]="  删除你的练习世界并重新开始？[y/N] "
MSG[menu_practice_ready]="  ${green}新的练习世界已准备就绪。${reset}"
MSG[menu_scores_prompt]="分数 - 按 q 返回"
MSG[menu_updating_try_later]="  ${yellow}回合结算正在进行中。${reset}请几分钟后再试。"
MSG[menu_unassigned]="  ${yellow}还没有国家分配给你的账号%s。${reset}
  请向游戏管理员申请一个（见菜单中的“如何加入”）。"
MSG[menu_opening]="正在打开你的国家 ${bold}%s${reset}。"
MSG[menu_nations]="本世界的国家：%s"
MSG[menu_nations_hint]="当游戏询问 \"What nation would you like to be\" 时，输入其中一个（或 god）。"
MSG[menu_disconnected]="${yellow}因回合结算，你已被断开连接。${reset}
你的指令已保存。几分钟后再回来，迎接新的回合。"
MSG[menu_cannot_enter]="${yellow}无法进入游戏。${reset}
请检查国家名称和密码。如果回合结算正在进行，
请几分钟后再试。"
MSG[menu_play]="进入游戏"
MSG[menu_join]="如何加入 / 回合如何进行"
MSG[menu_key_reference]="快捷键一览"
MSG[menu_scores]="分数"
MSG[menu_help]="完整帮助（游戏内的英文帮助画面）"
MSG[menu_not_done]="我的指令尚未完成"
MSG[menu_done]="本回合的指令已完成"
MSG[menu_practice]="练习世界（仅你一人，不计成绩）"
MSG[menu_log_out]="退出登录"
MSG[menu_goodbye]="再见，指挥官。"

# 加入向导 (join.sh)
MSG[join_questions]="有疑问请联系：${bold}%s${reset}"
MSG[join_title]="${bold}${green}建立你的国家${reset}"
MSG[join_welcome]="欢迎，${bold}%s${reset}。你的账号已就绪：现在来建立你的国家。"
MSG[join_too_late]="本局已进行到第 %s 回合：第 5 回合之后，新国家需由管理员添加。请联系管理员添加你的国家。"
MSG[join_builder]="
  ${bold}现在用游戏的国家创建器建立你的国家${reset}（其画面为英文）。

  它会询问：
    - ${bold}国家名称${reset}（最多 9 个字母）和${bold}国家密码${reset}
      （最多 7 个字符；每次进入游戏都要输入）
    - 统治者的名字、${bold}种族${reset}、${bold}职业${reset}和${bold}阵营${reset}
    - 地图标记：列表中任意一个未被占用的字母
  然后为你的国家分配点数。用 ${bold}j${reset} 和 ${bold}k${reset} 移动，
  按 ${bold}h${reset} 切换到增加模式，按 ${bold}Space${reset}（空格）购买。
  ${yellow}提示：${reset}给 ${bold}Treasury${reset}（国库）买 2 到 3 点；没有金币的国家
  第一回合无法征兵。按 ${bold}Esc${reset} 结束（剩余点数归入人口），
  然后回答 ${bold}y${reset} 保存。
"
MSG[join_open_builder]="  按任意键打开国家创建器..."
MSG[join_no_nation]="没有建立国家。在菜单中选择 1 再试一次。"
MSG[join_not_saved]="你的国家 %s 已建立，但无法与你的账号关联。请告知管理员。"
MSG[join_done]="
  ${bold}${green}欢迎加入游戏，%s 的统治者！${reset}

  从现在起，在菜单中选择 ${bold}1${reset} 来统治你的国家：游戏会要求输入
  你刚设置的国家密码。

  第一次玩 Conquer？菜单中的选项 7 是练习世界，Coach 按钮会带你
  完成第一个回合。
"
MSG[join_finish]="  按任意键继续..."
