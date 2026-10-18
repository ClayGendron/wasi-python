/*
 * Refuse the iconv conversions whose wasi-libc decoder gives wrong characters without an error
 * (spec 046, Decision 9): GB18030. wasi-sdk 33's wasi-libc decodes 1,617 of GB18030's 56,926 BMP
 * characters as other characters (the four-byte forms of U+F900 to U+FFFD come back shifted);
 * musl fixed its decoder after 1.2.6 and wasi-libc has not taken it yet
 * (context/upstream/15-wasi-libc-gb18030-decoder/). Silently wrong text is worse than an error,
 * so iconv_open refuses the encoding as it refuses any it lacks, and libxml2, its one caller in
 * the binary, raises its own "Unsupported encoding" error.
 *
 * Step 60 compiles this file into the reactor's link with -Wl,--wrap=iconv_open, so every call to
 * iconv_open reaches __wrap_iconv_open and the real one is __real_iconv_open. It changes no
 * upstream source. Remove it, and its --wrap, when a wasi-sdk release carries musl's fix (the
 * judge's encodings check turns red that day).
 */
#include <ctype.h>
#include <errno.h>
#include <iconv.h>
#include <stddef.h>

iconv_t __real_iconv_open(const char *to, const char *from);

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
    if (is_gb18030(to) || is_gb18030(from)) {
        errno = EINVAL;
        return (iconv_t)-1;
    }
    return __real_iconv_open(to, from);
}
