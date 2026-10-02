/*
 * SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * conqowner - show or set the Unix uid that owns the god nation (nation 0).
 *
 * Conquer is built with CHECKUSER: every nation belongs to a Unix uid and
 * "conqrun -a" refuses to add a second nation for the same uid unless that
 * uid also owns the god nation. In the web container every player and the
 * administrator run as the same user, so the god nation must belong to that
 * user or only one nation could ever be created. Worlds generated elsewhere
 * (e.g. with generate-world.sh) carry the uid of the user who made them.
 *
 * Built against the Conquer headers so the data file layout always matches
 * the compiled game.
 *
 * Usage: conqowner [-d DIR] [-s UID]
 *   -d DIR  world directory (default: DEFAULTDIR)
 *   -s UID  set the god nation owner to UID
 */

#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
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
	long newuid = -1;
	struct stat st;
	off_t sectors, expected, offset;
	short int uid;
	int fd, opt;

	while ((opt = getopt(argc, argv, "d:s:")) != -1) {
		switch (opt) {
		case 'd':
			dir = optarg;
			break;
		case 's':
			newuid = strtol(optarg, NULL, 10);
			break;
		default:
			fprintf(stderr, "usage: %s [-d DIR] [-s UID]\n", argv[0]);
			return 2;
		}
	}

	if (chdir(dir) != 0) {
		fprintf(stderr, "conqowner: cannot change dir to %s\n", dir);
		return 1;
	}
	fd = open("data", newuid >= 0 ? O_RDWR : O_RDONLY);
	if (fd < 0 || fstat(fd, &st) != 0) {
		fprintf(stderr, "conqowner: cannot open %s/data\n", dir);
		return 1;
	}
	if (read(fd, &world, sizeof(world)) != (ssize_t) sizeof(world)) {
		fprintf(stderr, "conqowner: cannot read world header\n");
		return 1;
	}

	/*
	 * Army and capital coordinates are unsigned char, so positions on
	 * larger maps wrap around: armies end up in the water and players
	 * see an empty map. conqrun -m does not prevent such worlds.
	 */
	if (MAPX > 256 || MAPY > 256)
		fprintf(stderr, "conqowner: WARNING: world is %dx%d, but Conquer only "
			"supports maps up to 256x256; generate a smaller world\n",
			(int) MAPX, (int) MAPY);

	/* data file = world header, MAPX*MAPY sectors, NTOTAL nations */
	sectors = (off_t) MAPX * MAPY * sizeof(struct s_sector);
	expected = sizeof(world) + sectors + NTOTAL * sizeof(struct s_nation);
	if (st.st_size != expected) {
		fprintf(stderr, "conqowner: unexpected data file size %ld (expected %ld)\n",
			(long) st.st_size, (long) expected);
		return 1;
	}

	offset = sizeof(world) + sectors + offsetof(struct s_nation, uid);
	if (pread(fd, &uid, sizeof(uid), offset) != (ssize_t) sizeof(uid)) {
		fprintf(stderr, "conqowner: cannot read god nation owner\n");
		return 1;
	}

	if (newuid < 0 || newuid == uid) {
		printf("%d\n", uid);
		return 0;
	}

	uid = (short int) newuid;
	if (pwrite(fd, &uid, sizeof(uid), offset) != (ssize_t) sizeof(uid)) {
		fprintf(stderr, "conqowner: cannot write god nation owner\n");
		return 1;
	}
	printf("%d\n", uid);
	return close(fd) == 0 ? 0 : 1;
}
