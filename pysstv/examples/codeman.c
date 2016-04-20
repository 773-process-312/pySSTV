#include <stdio.h>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include "stb_image.h"
#include "codegen.c"

int main(int argc, char **argv) {
	int x, y, n;
	unsigned char *img = stbi_load(argv[1], &x, &y, &n, 0);

	float freqs[FREQ_COUNT], msecs[FREQ_COUNT];

	convert(img, freqs, msecs, x);

	for (int i = 0; i < FREQ_COUNT; i++) {
		fwrite(&(freqs[i]), 4, 1, stdout);
		fwrite(&(msecs[i]), 4, 1, stdout);
	}

	return 0;
}
