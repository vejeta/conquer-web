/* SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * The small part of curses that Conquer uses, for the WebAssembly build.
 * shim.c keeps an 80x24 screen and draws it on xterm.js with ANSI codes.
 */
#ifndef CONQUER_WASM_CURSES_H
#define CONQUER_WASM_CURSES_H

#include <stdio.h>

typedef struct { int unused; } WINDOW;
typedef unsigned long chtype;

extern WINDOW *stdscr, *curscr;
extern int LINES, COLS;
extern int shim_cury, shim_curx;

#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif
#ifndef ERR
#define ERR (-1)
#endif
#ifndef OK
#define OK 0
#endif

WINDOW *initscr(void);
int endwin(void);
int refresh(void);
int wrefresh(WINDOW *);
int getch(void);
int move(int, int);
int clear(void);
int erase(void);
int clrtoeol(void);
int clrtobot(void);
int addch(int);
int mvaddch(int, int, int);
int addstr(const char *);
int mvaddstr(int, int, const char *);
int printw(const char *, ...);
int mvprintw(int, int, const char *, ...);
int standout(void);
int standend(void);
int beep(void);
int box(WINDOW *, int, int);

#define getyx(w, y, x) ((y) = shim_cury, (x) = shim_curx)
#define cbreak() 0
#define nocbreak() 0
#define crmode() 0
#define nocrmode() 0
#define raw() 0
#define noraw() 0
#define echo() 0
#define noecho() 0
#define savetty() 0
#define resetty() 0

#endif
