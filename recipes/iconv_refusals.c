/*
 * Refuse the iconv conversions whose wasi-libc decoder gives wrong characters without an error
 * (spec 046, Decision 9): GB18030. wasi-sdk 34's wasi-libc, as 33's did, decodes 1,617 of GB18030's
 * 56,926 BMP characters as other characters (the four-byte forms of U+F900 to U+FFFD come back
 * shifted); musl fixed its decoder after 1.2.6, and wasi-sdk 34's iconv.c is musl 1.2.6's (spec 086)
 * (context/upstream/15-wasi-libc-gb18030-decoder/). Silently wrong text is worse than an error.
 *
 * Decoding from GB18030 opens, and its handle passes ASCII through (GB18030's own single-byte
 * range, so that is the right decoding) and fails on the first byte above it as an invalid byte
 * would (EILSEQ). An open that failed would not do: libxml2's HTML parser and its recover mode go
 * on in their fallback encoding (windows-1252) when an encoding is unsupported, and read every
 * non-ASCII character of a GB18030 page wrongly without raising (the build review's finding 1);
 * and the HTML parser opens a declared encoding only if it passes ASCII through unchanged. A
 * failed conversion instead raises "Invalid bytes in character encoding" in strict XML, and in
 * the HTML parser and in recover mode ends the text there: nothing is decoded wrongly.
 * Encoding to GB18030 is refused at the open (EINVAL), as wasi-libc cannot encode it anyway, so
 * lxml's own encoding lookups (a serializer's or a parser's `encoding=`) raise LookupError.
 *
 * Step 60 compiles this file into the reactor's link with -Wl,--wrap=iconv_open,
 * -Wl,--wrap=iconv and -Wl,--wrap=iconv_close, so each call reaches __wrap_* and the real
 * functions are __real_*. libxml2's encoding.c is their one caller in the binary. It changes no
 * upstream source. Remove it, and its --wrap flags, when a wasi-sdk release carries musl's fix
 * (the judge's encodings check turns red that day).
 */
#include <ctype.h>
#include <errno.h>
#include <iconv.h>
#include <stddef.h>

iconv_t __real_iconv_open(const char *to, const char *from);
size_t __real_iconv(iconv_t cd, char **in, size_t *inleft, char **out, size_t *outleft);
int __real_iconv_close(iconv_t cd);

/* The handle of a refused decoder: an address no real iconv_open returns. musl's handles are odd
 * integers (f<<16 | t<<1 | 1) or heap pointers; an int's address is even and static. */
static int refused;
#define REFUSED ((iconv_t)&refused)

/* Whether an encoding name is GB18030, ignoring case and punctuation ("GB-18030", "gb_18030"). */
static int is_gb18030(const char *name)
{
    static const char want[] = "gb18030";
    const char *w = want;
    if (name == NULL) {
        return 0;
    }
    for (; *name; name++) {
        if (!isalnum((unsigned char)*name)) {
            continue;
        }
        if (*w == '\0' || tolower((unsigned char)*name) != *w) {
            return 0;
        }
        w++;
    }
    return *w == '\0';
}

iconv_t __wrap_iconv_open(const char *to, const char *from)
{
    if (is_gb18030(to)) {
        errno = EINVAL;
        return (iconv_t)-1;
    }
    if (is_gb18030(from)) {
        return REFUSED;
    }
    return __real_iconv_open(to, from);
}

size_t __wrap_iconv(iconv_t cd, char **in, size_t *inleft, char **out, size_t *outleft)
{
    if (cd == REFUSED) {
        if (in == NULL || *in == NULL || inleft == NULL) {
            return 0; /* a reset converts nothing, and is no error */
        }
        /* ASCII is GB18030's own single-byte range, so it passes through unchanged; the first
         * byte above it fails as an invalid one would. */
        while (*inleft > 0 && (unsigned char)**in < 0x80) {
            if (out == NULL || *out == NULL || outleft == NULL || *outleft == 0) {
                errno = E2BIG;
                return (size_t)-1;
            }
            *(*out)++ = *(*in)++;
            (*inleft)--;
            (*outleft)--;
        }
        if (*inleft > 0) {
            errno = EILSEQ;
            return (size_t)-1;
        }
        return 0;
    }
    return __real_iconv(cd, in, inleft, out, outleft);
}

int __wrap_iconv_close(iconv_t cd)
{
    if (cd == REFUSED) {
        return 0;
    }
    return __real_iconv_close(cd);
}
