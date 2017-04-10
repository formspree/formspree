/*
 * Copyright (c) 1997, 1998, 1999, 2000, 2001, 2002, 2004, 2005, 2008, 2009
 *      Inferno Nettverk A/S, Norway.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. The above copyright notice, this list of conditions and the following
 *    disclaimer must appear in all copies of the software, derivative works
 *    or modified versions, and any portions thereof, aswell as in all
 *    supporting documentation.
 * 2. All advertising materials mentioning features or use of this software
 *    must display the following acknowledgement:
 *      This product includes software developed by
 *      Inferno Nettverk A/S, Norway.
 * 3. The name of the author may not be used to endorse or promote products
 *    derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Inferno Nettverk A/S requests users of this software to return to
 *
 *  Software Distribution Coordinator  or  sdc@inet.no
 *  Inferno Nettverk A/S
 *  Oslo Research Park
 *  Gaustadalléen 21
 *  NO-0349 Oslo
 *  Norway
 *
 * any improvements or extensions that they make and grant Inferno Nettverk A/S
 * the rights to redistribute these changes.
 *
 */

/* $Id: socks.h.in,v 1.22 2009/12/19 14:14:28 karls Exp $ */

#include <sys/types.h>
#include <sys/socket.h>

/*
 * The definition of bindresvport below might conflict with
 * <netinet/in.h> ... best workaround seems to be to make sure the
 * file is included prior to the #define
 */
#include <netinet/in.h>

#include <netdb.h>


#define accept Raccept
#define bind Rbind
#define bindresvport Rbindresvport
#define connect Rconnect
#define gethostbyname Rgethostbyname
#define gethostbyname2 Rgethostbyname2
#define getaddrinfo Rgetaddrinfo
#define getipnodebyname Rgetipnodebyname
#define getpeername Rgetpeername
#define getsockname Rgetsockname
#define getsockopt Rgetsockopt
#define listen Rlisten
#define read Rread
#define readv Rreadv
#define recv Rrecv
#define recvfrom Rrecvfrom
#define recvfrom Rrecvfrom
#define recvmsg Rrecvmsg
#define rresvport Rrresvport
#define send Rsend
#define sendmsg Rsendmsg
#define sendto Rsendto
#define write Rwrite
#define writev Rwritev

int
SOCKSinit(char *progname);
/*
 * If you want to, call this function with "progname" as the name of
 * your program.  For systems that do not have __progname.
 * Returns:
 *      On success: 0.
*/

int Raccept(int, struct sockaddr *, socklen_t *);
int Rconnect(int, const struct sockaddr *, socklen_t);
int Rgetsockname(int, struct sockaddr *, socklen_t *);
int Rgetsockopt(int, int, int, void *, socklen_t *);
int Rgetpeername(int, struct sockaddr *, socklen_t *);
ssize_t Rsendto(int s, const void *msg, size_t len, int flags,
      const struct sockaddr *to, socklen_t tolen);
ssize_t Rrecvfrom(int s, void *buf, size_t len, int flags,
      struct sockaddr * from, socklen_t *fromlen);
ssize_t Rsendmsg(int s, const struct msghdr *msg, int flags);
ssize_t Rrecvmsg(int s, struct msghdr *msg, int flags);
int Rbind(int, const struct sockaddr *, socklen_t);

int Rbindresvport(int, struct sockaddr_in *);
int Rrresvport(int *);
struct hostent *Rgethostbyname(const char *);
struct hostent *Rgethostbyname2(const char *, int af);
int Rgetaddrinfo(const char *nodename, const char *servname,
      const struct addrinfo *hints, struct addrinfo **res);
struct hostent *Rgetipnodebyname(const char *name, int af, int flags,
      int *error_num);
ssize_t Rwrite(int d, const void *buf, size_t nbytes);
ssize_t Rwritev(int d, const struct iovec *iov, int iovcnt);
ssize_t Rsend(int s, const void *msg, size_t len, int flags);
ssize_t Rread(int d, void *buf, size_t nbytes);
ssize_t Rreadv(int d, const struct iovec *iov, int iovcnt);
ssize_t Rrecv(int s, void *msg, size_t len, int flags);

int Rlisten(int, int);
int Rselect(int, fd_set *, fd_set *, fd_set *, struct timeval *);
