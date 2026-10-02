/* SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Included before every game source file in the WebAssembly build
 * (emcc -include shim.h). The browser has no users, no blocking keyboard
 * and no shell, so these calls go to shim.c instead.
 */
#define getuid shim_getuid
#define geteuid shim_getuid
#define getpwnam shim_getpwnam
#define getpwuid shim_getpwuid
#define getpass shim_getpass
#define sleep shim_sleep
#define system shim_system
/* getchar is declared by stdio.h: rename the calls only, after it */
#include <stdio.h>
#undef getchar
#define getchar() shim_getchar()
int shim_getchar(void);
