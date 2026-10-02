/*
 * SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * conqpasswd - set the password of a nation, god included, without knowing
 * the old one. The game only lets a nation change its password from inside
 * (and god must log in first), so a forgotten god password would lock the
 * administrator out.
 *
 * The new password is read from standard input (one line), so it never
 * shows in the process list. It works at once, and replaces any password
 * change the nation ordered this turn only if run after the next update.
 *
 * Built against the Conquer headers so the data file layout and the
 * password encryption always match the game.
 *
 * With -l the password is locked instead: no password opens the nation.
 * The default world in the repository ships with god locked, since the
 * game keeps only seven characters of a DES crypt and anyone could guess
 * a password back from a published world (and god's opens every nation).
 * With -q nothing changes: the exit status says 3 if the nation's
 * password is locked, 0 if one is set.
 *
 * Usage: conqpasswd [-d DIR] [-l | -q] NATION < password
 */

/* No crypt() output starts with '*', so this matches no password */
#define LOCKED "*LOCKED"

#include <crypt.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* data.h declares the game's own main(); keep it out of the way */
#define main conquer_main
#include "header.h"
#include "data.h"
#undef main

struct s_world world;

int
main(int argc, char **argv)
{
	const char *dir = DEFAULTDIR;
	struct s_nation nation;
	struct stat st;
	off_t sectors, expected, offset;
	char line[256], hash[PASSLTH + 1];
	const char *crypted;
	size_t len;
	int fd, opt, n, min, lock = 0, query = 0;

	while ((opt = getopt(argc, argv, "d:lq")) != -1) {
		if (opt == 'd')
			dir = optarg;
		else if (opt == 'l')
			lock = 1;
		else if (opt == 'q')
			query = 1;
		else {
			fprintf(stderr, "usage: %s [-d DIR] [-l | -q] NATION < password\n", argv[0]);
			return 2;
		}
	}
	if (optind != argc - 1 || (lock && query)) {
		fprintf(stderr, "usage: %s [-d DIR] [-l | -q] NATION < password\n", argv[0]);
		return 2;
	}

	len = 0;
	if (!lock && !query) {
		if (fgets(line, sizeof(line), stdin) == NULL) {
			fprintf(stderr, "conqpasswd: no password given\n");
			return 1;
		}
		line[strcspn(line, "\r\n")] = '\0';
		len = strlen(line);
	}

	if (chdir(dir) != 0) {
		fprintf(stderr, "conqpasswd: cannot change dir to %s\n", dir);
		return 1;
	}
	fd = open("data", query ? O_RDONLY : O_RDWR);
	if (fd < 0 || fstat(fd, &st) != 0) {
		fprintf(stderr, "conqpasswd: cannot open %s/data\n", dir);
		return 1;
	}
	if (read(fd, &world, sizeof(world)) != (ssize_t) sizeof(world)) {
		fprintf(stderr, "conqpasswd: cannot read world header\n");
		return 1;
	}
	/* data file = world header, MAPX*MAPY sectors, NTOTAL nations */
	sectors = (off_t) MAPX * MAPY * sizeof(struct s_sector);
	expected = sizeof(world) + sectors + NTOTAL * sizeof(struct s_nation);
	if (st.st_size != expected) {
		fprintf(stderr, "conqpasswd: unexpected data file size %ld (expected %ld)\n",
			(long) st.st_size, (long) expected);
		return 1;
	}

	for (n = 0; n < NTOTAL; n++) {
		offset = sizeof(world) + sectors + (off_t) n * sizeof(struct s_nation);
		if (pread(fd, &nation, sizeof(nation), offset) != (ssize_t) sizeof(nation)) {
			fprintf(stderr, "conqpasswd: cannot read nation %d\n", n);
			return 1;
		}
		/* God logs in as "god"; its nation is called "unowned" */
		if (strcmp(nation.name, argv[optind]) == 0
		    || (n == 0 && strcmp(argv[optind], "god") == 0))
			break;
	}
	if (n == NTOTAL) {
		fprintf(stderr, "conqpasswd: no nation named '%s'\n", argv[optind]);
		return 1;
	}

	if (query) {
		if (strncmp(nation.passwd, LOCKED, PASSLTH) == 0) {
			printf("The password of %s is locked\n", n == 0 ? "god" : nation.name);
			return 3;
		}
		printf("The password of %s is set\n", n == 0 ? "god" : nation.name);
		return 0;
	}

	memset(hash, 0, sizeof(hash));
	if (lock) {
		strncpy(hash, LOCKED, PASSLTH);
	} else {
		/* The game's own limits: god at least 4 characters, nations 2 */
		min = n == 0 ? 4 : 2;
		if ((int) len < min || len > PASSLTH) {
			fprintf(stderr, "conqpasswd: the password of %s must have %d to %d characters\n",
				n == 0 ? "god" : nation.name, min, PASSLTH);
			return 1;
		}
		crypted = crypt(line, SALT);
		if (crypted == NULL) {
			fprintf(stderr, "conqpasswd: crypt failed\n");
			return 1;
		}
		strncpy(hash, crypted, PASSLTH);
	}
	offset += offsetof(struct s_nation, passwd);
	if (pwrite(fd, hash, sizeof(hash), offset) != (ssize_t) sizeof(hash)) {
		fprintf(stderr, "conqpasswd: cannot write the password\n");
		return 1;
	}
	if (close(fd) != 0) {
		fprintf(stderr, "conqpasswd: cannot write %s/data\n", dir);
		return 1;
	}
	printf(lock ? "Password of %s locked\n" : "Password of %s changed\n", n == 0 ? "god" : nation.name);
	return 0;
}
