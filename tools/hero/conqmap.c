/*
 * SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * conqmap - print a Conquer world as JSON for the landing page's map:
 * size, nations (name, mark) and, per row, 4 characters per sector:
 * altitude, designation and the owner's nation id in hex.
 *
 * Built against the Conquer headers (see build-map.py), so the data file
 * layout always matches the game.
 *
 * Usage: conqmap WORLD_DIR/data
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#define main conquer_main
#include "header.h"
#include "data.h"
#undef main
struct s_world world;
int main(int argc, char **argv)
{
	int fd = open(argv[1], O_RDONLY), x, y, n;
	struct s_sector *s; struct s_nation *nt;
	read(fd, &world, sizeof(world));
	s = malloc(MAPX * MAPY * sizeof(*s));
	read(fd, s, MAPX * MAPY * sizeof(*s));
	nt = malloc(NTOTAL * sizeof(*nt));
	read(fd, nt, NTOTAL * sizeof(*nt));
	printf("{\"w\":%d,\"h\":%d,\"nations\":[", (int) MAPX, (int) MAPY);
	for (n = 0; n < NTOTAL; n++)
		printf("%s{\"id\":%d,\"name\":\"%s\",\"mark\":\"%c\",\"active\":%d,\"cx\":%d,\"cy\":%d}", n ? "," : "",
		       n, nt[n].name, nt[n].mark ? nt[n].mark : ' ', nt[n].active, nt[n].capx, nt[n].capy);
	printf("],\"rows\":[");
	for (y = 0; y < MAPY; y++) {
		printf("%s\"", y ? "," : "");
		for (x = 0; x < MAPX; x++) {
			struct s_sector *c = &s[x * MAPY + y];
			putchar(c->altitude ? c->altitude : '?');
			putchar(c->designation ? c->designation : ' ');
			printf("%02x", c->owner);
		}
		printf("\"");
	}
	printf("]}\n");
	return 0;
}
