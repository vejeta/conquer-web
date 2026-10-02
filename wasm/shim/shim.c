/* SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Runtime for the WebAssembly build of Conquer:
 *  - a minimal curses: an 80x24 screen redrawn on xterm.js with ANSI codes
 *    (only the lines that changed);
 *  - the keyboard: the page queues keys in Module.conquerKeys, and reads
 *    wait for them without blocking the browser (Asyncify);
 *  - one user, "conquer" (uid 1000), who owns the practice nation and may
 *    run turn updates; getpass, sleep and the few system() calls.
 */
#include <emscripten.h>
#include <pwd.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include "curses.h"

#define ROWS 24
#define WIDTH 80

static WINDOW the_screen;
WINDOW *stdscr = &the_screen, *curscr = &the_screen;
int LINES = ROWS, COLS = WIDTH;
int shim_cury, shim_curx;

static char scr[ROWS][WIDTH], shown[ROWS][WIDTH];
static unsigned char att[ROWS][WIDTH], shown_att[ROWS][WIDTH];
static int reverse_on, repaint_all = 1;

/* ---- keyboard ---- */

EM_JS(int, js_key_count, (void), {
    return Module.conquerKeys ? Module.conquerKeys.length : 0;
});
EM_JS(int, js_next_key, (void), {
    return Module.conquerKeys.shift();
});
/* Scripted runs (make-world.js) have no keyboard: out of keys, stop */
EM_JS(int, js_keys_closed, (void), {
    return Module.conquerKeysClosed ? 1 : 0;
});

static int read_key(void)
{
    fflush(stdout);
    while (!js_key_count()) {
        if (js_keys_closed()) {
            fputs("\n[out of scripted keys]\n", stderr);
            exit(3);
        }
        emscripten_sleep(15);
    }
    return js_next_key();
}

int getch(void)
{
    int c = read_key();
    return c == '\r' ? '\n' : c;   /* curses translates Return to newline */
}

int shim_getchar(void)
{
    int c = getch();
    if (c >= 32 && c < 127) putchar(c);
    if (c == '\n') fputs("\r\n", stdout);
    fflush(stdout);
    return c;
}

char *shim_getpass(const char *prompt)
{
    static char buf[64];
    size_t n = 0;
    int c;
    fputs(prompt, stdout);
    while ((c = getch()) != '\n') {
        if ((c == 127 || c == '\b') && n > 0) n--;
        else if (c >= 32 && c < 127 && n < sizeof(buf) - 1) buf[n++] = (char) c;
    }
    buf[n] = '\0';
    fputs("\r\n", stdout);
    fflush(stdout);
    return buf;
}

unsigned int shim_sleep(unsigned int seconds)
{
    fflush(stdout);
    emscripten_sleep(seconds * 1000);
    return 0;
}

/* The only commands the game runs: "cat FILE >> FILE" (mail and news),
 * and conqsort, which only sorts the newspaper and is skipped */
int shim_system(const char *command)
{
    char from[256], to[256];
    if (sscanf(command, "cat %255s >> %255s", from, to) == 2) {
        FILE *in = fopen(from, "r"), *out = fopen(to, "a");
        int c;
        if (in && out)
            while ((c = getc(in)) != EOF) putc(c, out);
        if (in) fclose(in);
        if (out) fclose(out);
    }
    return 0;
}

/* ---- the one user ---- */

static struct passwd conquer_user = { "conquer", "x", 1000, 1000, "Conquer", "/conquer", "/bin/sh" };

uid_t shim_getuid(void) { return 1000; }

struct passwd *shim_getpwnam(const char *name)
{
    return name && strcmp(name, "conquer") == 0 ? &conquer_user : NULL;
}

struct passwd *shim_getpwuid(uid_t uid)
{
    return uid == 1000 ? &conquer_user : NULL;
}

/* ---- screen ---- */

WINDOW *initscr(void)
{
    memset(scr, ' ', sizeof(scr));
    memset(att, 0, sizeof(att));
    shim_cury = shim_curx = 0;
    repaint_all = 1;
    fputs("\033[?1049h\033[H\033[2J", stdout);
    return stdscr;
}

int endwin(void)
{
    refresh();
    fputs("\033[0m\033[?1049l", stdout);
    fflush(stdout);
    return OK;
}

int move(int y, int x)
{
    if (y < 0) y = 0;
    if (y >= ROWS) y = ROWS - 1;
    if (x < 0) x = 0;
    if (x >= WIDTH) x = WIDTH - 1;
    shim_cury = y;
    shim_curx = x;
    return OK;
}

int clrtoeol(void)
{
    memset(&scr[shim_cury][shim_curx], ' ', WIDTH - shim_curx);
    memset(&att[shim_cury][shim_curx], 0, WIDTH - shim_curx);
    return OK;
}

int clrtobot(void)
{
    int y;
    clrtoeol();
    for (y = shim_cury + 1; y < ROWS; y++) {
        memset(scr[y], ' ', WIDTH);
        memset(att[y], 0, WIDTH);
    }
    return OK;
}

int erase(void)
{
    memset(scr, ' ', sizeof(scr));
    memset(att, 0, sizeof(att));
    shim_cury = shim_curx = 0;
    return OK;
}

int clear(void)
{
    erase();
    repaint_all = 1;
    return OK;
}

int addch(int c)
{
    c &= 0xff;
    if (c == '\n') {
        clrtoeol();
        if (shim_cury < ROWS - 1) shim_cury++;
        shim_curx = 0;
        return OK;
    }
    if (c == '\r') { shim_curx = 0; return OK; }
    if (c == '\t') {
        do addch(' '); while (shim_curx % 8 && shim_curx > 0);
        return OK;
    }
    if (c == '\b') {
        if (shim_curx > 0) shim_curx--;
        return OK;
    }
    if (c < 32 || c > 126) c = '?';
    scr[shim_cury][shim_curx] = (char) c;
    att[shim_cury][shim_curx] = (unsigned char) reverse_on;
    if (++shim_curx >= WIDTH) {
        shim_curx = 0;
        if (shim_cury < ROWS - 1) shim_cury++;
    }
    return OK;
}

int mvaddch(int y, int x, int c) { move(y, x); return addch(c); }

int addstr(const char *s)
{
    while (*s) addch((unsigned char) *s++);
    return OK;
}

int mvaddstr(int y, int x, const char *s) { move(y, x); return addstr(s); }

int printw(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    return addstr(buf);
}

int mvprintw(int y, int x, const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    move(y, x);
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    return addstr(buf);
}

int standout(void) { reverse_on = 1; return OK; }
int standend(void) { reverse_on = 0; return OK; }

int beep(void)
{
    fputs("\a", stdout);
    return OK;
}

int box(WINDOW *w, int v, int h)
{
    int x, y;
    (void) w;
    for (x = 0; x < WIDTH; x++) {
        scr[0][x] = scr[ROWS - 1][x] = (char) (h ? h : '-');
    }
    for (y = 0; y < ROWS; y++) {
        scr[y][0] = scr[y][WIDTH - 1] = (char) (v ? v : '|');
    }
    return OK;
}

/* Draw the lines that changed since the last refresh */
int refresh(void)
{
    int y, x, rev;
    char buf[32];
    for (y = 0; y < ROWS; y++) {
        if (!repaint_all && !memcmp(scr[y], shown[y], WIDTH) && !memcmp(att[y], shown_att[y], WIDTH))
            continue;
        snprintf(buf, sizeof(buf), "\033[%d;1H\033[0m", y + 1);
        fputs(buf, stdout);
        rev = 0;
        for (x = 0; x < WIDTH; x++) {
            if (att[y][x] != rev) {
                rev = att[y][x];
                fputs(rev ? "\033[7m" : "\033[0m", stdout);
            }
            putchar(scr[y][x]);
        }
        if (rev) fputs("\033[0m", stdout);
        memcpy(shown[y], scr[y], WIDTH);
        memcpy(shown_att[y], att[y], WIDTH);
    }
    repaint_all = 0;
    snprintf(buf, sizeof(buf), "\033[%d;%dH", shim_cury + 1, shim_curx + 1);
    fputs(buf, stdout);
    fflush(stdout);
    return OK;
}

int wrefresh(WINDOW *w)
{
    (void) w;
    repaint_all = 1;   /* Ctrl-L: redraw everything */
    return refresh();
}
