/*
 * fake_uid.so - Contournement QNAP execve + propriété overlay2
 *
 * Problème 1: postgres/initdb refusent UID=0 (root)
 * → intercepter getuid/geteuid pour retourner UID 70 (postgres)
 *
 * Problème 2: initdb chown les fichiers vers UID 70, mais postgres --boot
 * (child process) tourne parfois sans LD_PRELOAD et root QNAP ne peut
 * pas accéder aux fichiers owned par non-root dans overlay2
 * → NOP tous les chown/fchown pour garder les fichiers owned par root
 *
 * Usage: LD_PRELOAD=/fake_uid.so initdb/postgres ...
 */
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>

#define PG_UID ((uid_t)70)
#define PG_GID ((gid_t)70)

/* Intercepter getuid/geteuid → postgres pense tourner comme UID 70 */
uid_t getuid(void)  { return PG_UID; }
uid_t geteuid(void) { return PG_UID; }
gid_t getgid(void)  { return PG_GID; }
gid_t getegid(void) { return PG_GID; }

int getresuid(uid_t *ruid, uid_t *euid, uid_t *suid) {
    if (ruid) *ruid = PG_UID;
    if (euid) *euid = PG_UID;
    if (suid) *suid = PG_UID;
    return 0;
}

int getresgid(gid_t *rgid, gid_t *egid, gid_t *sgid) {
    if (rgid) *rgid = PG_GID;
    if (egid) *egid = PG_GID;
    if (sgid) *sgid = PG_GID;
    return 0;
}

/* NOP chown + chmod → tout reste owned root et lisible root → root accède toujours
 * Postgres vérifie que le data dir n'est pas world-writable (mode & 0002).
 * Les fichiers sont créés avec umask par défaut (0644/0755), ce qui convient. */
int chown(const char *path, uid_t owner, gid_t group)              { (void)path; (void)owner; (void)group; return 0; }
int fchown(int fd, uid_t owner, gid_t group)                       { (void)fd; (void)owner; (void)group; return 0; }
int lchown(const char *path, uid_t owner, gid_t group)             { (void)path; (void)owner; (void)group; return 0; }
int fchownat(int dirfd, const char *path, uid_t o, gid_t g, int f) { (void)dirfd; (void)path; (void)o; (void)g; (void)f; return 0; }
int chmod(const char *path, mode_t mode)                           { (void)path; (void)mode; return 0; }
int fchmod(int fd, mode_t mode)                                    { (void)fd; (void)mode; return 0; }
int fchmodat(int dirfd, const char *path, mode_t mode, int flags)  { (void)dirfd; (void)path; (void)mode; (void)flags; return 0; }
