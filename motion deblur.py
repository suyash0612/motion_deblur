from __future__ import print_function

import numpy as np
import cv2
import os



def blur_edge(img, d=31):
    h, w  = img.shape[:2]
    img_pad = cv2.copyMakeBorder(img, d, d, d, d, cv2.BORDER_WRAP)
    img_blur = cv2.GaussianBlur(img_pad, (2*d+1, 2*d+1), -1)[d:-d,d:-d]
    y, x = np.indices((h, w))
    dist = np.dstack([x, w-x-1, y, h-y-1]).min(-1)
    w = np.minimum(np.float32(dist)/d, 1.0)
    return img*w + img_blur*(1-w)

def motion_kernel(angle, d, sz=65):
    kern = np.ones((1, d), np.float32)
    c, s = np.cos(angle), np.sin(angle)
    A = np.float32([[c, -s, 0], [s, c, 0]])
    sz2 = sz // 2
    A[:,2] = (sz2, sz2) - np.dot(A[:,:2], ((d-1)*0.5, 0))
    kern = cv2.warpAffine(kern, A, (sz, sz), flags=cv2.INTER_CUBIC)
    
    return kern

def defocus_kernel(d, sz=65):
    kern = np.zeros((sz, sz), np.uint8)
    cv2.circle(kern, (sz, sz), d, 255, -1, cv2.CV_AA, shift=1)
    kern = np.float32(kern) / 255.0
    return kern


if __name__ == '__main__':
    print(__doc__)
    import sys, getopt
    opts, args = getopt.getopt(sys.argv[1:], 'f:', ['circle', 'angle=', 'd=', 'snr='])
    opts = dict(opts)
    try:
        fn = args[0]
    except:
        fn = os.getcwd()+'\\blurry images input\\'+'car.jpg'

    win = 'deconvolution'

    img_bw = cv2.imread(fn, 0)
    img_rgb = cv2.imread(fn, 1)

    if img_bw is None and img_rgb is None:
        print('Failed to load image:', fn)
        sys.exit(1)

    img_r = np.zeros_like(img_bw)
    img_g = np.zeros_like(img_bw)
    img_b = np.zeros_like(img_bw)

    img_r = img_rgb[..., 0]
    img_g = img_rgb[..., 1]
    
    img_b = img_rgb[..., 2]

    img_rgb = np.float32(img_rgb)/255.0
    img_bw = np.float32(img_bw)/255.0
    img_r = np.float32(img_r)/255.0
    img_g = np.float32(img_g)/255.0
    img_b = np.float32(img_b)/255.0

    cv2.imshow('input', img_rgb)

    # img_bw = blur_edge(img_bw)
    img_r = blur_edge(img_r)
    img_g = blur_edge(img_g)
    img_b = blur_edge(img_b)

    # IMG_BW = cv2.dft(img_bw, flags=cv2.DFT_COMPLEX_OUTPUT)
    IMG_R = cv2.dft(img_r, flags=cv2.DFT_COMPLEX_OUTPUT)
    IMG_G = cv2.dft(img_g, flags=cv2.DFT_COMPLEX_OUTPUT)
    IMG_B = cv2.dft(img_b, flags=cv2.DFT_COMPLEX_OUTPUT)

    defocus = '--circle' in opts

    def update(_):
        ang = np.deg2rad( cv2.getTrackbarPos('angle', win) )
        d = cv2.getTrackbarPos('d', win)
        noise = 10**(-0.1*cv2.getTrackbarPos('SNR (db)', win))

        if defocus:
            psf = defocus_kernel(d)
        else:
            psf = motion_kernel(ang, d)
        cv2.imshow('psf', psf)
        #print(psf)
        psf /= psf.sum()
        psf_pad = np.zeros_like(img_bw)
        kh, kw = psf.shape
        psf_pad[:kh, :kw] = psf
        PSF = cv2.dft(psf_pad, flags=cv2.DFT_COMPLEX_OUTPUT, nonzeroRows = kh)
        PSF2 = (PSF**2).sum(-1)
        iPSF = PSF / (PSF2 + noise)[...,np.newaxis]

        # RES_BW = cv2.mulSpectrums(IMG_BW, iPSF, 0)
        RES_R = cv2.mulSpectrums(IMG_R, iPSF, 0)
        RES_G = cv2.mulSpectrums(IMG_G, iPSF, 0)
        RES_B = cv2.mulSpectrums(IMG_B, iPSF, 0)


        # res_bw = cv2.idft(RES_BW, flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT )
        res_r = cv2.idft(RES_R, flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT )
        res_g = cv2.idft(RES_G, flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT )
        res_b = cv2.idft(RES_B, flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT )

        res_rgb = np.zeros_like(img_rgb)
        res_rgb[..., 0] = res_r
        res_rgb[..., 1] = res_g
        res_rgb[..., 2] = res_b

        # res_bw = np.roll(res_bw, -kh//2, 0)
        # res_bw = np.roll(res_bw, -kw//2, 1)
        res_rgb = np.roll(res_rgb, -kh//2, 0)
        res_rgb = np.roll(res_rgb, -kw//2, 1)
        cv2.imshow(win, res_rgb)

    cv2.namedWindow(win)
    cv2.namedWindow('psf', 0)
    cv2.createTrackbar('angle', win, int(opts.get('--angle', 135)), 180, update)
    cv2.createTrackbar('d', win, int(opts.get('--d', 22)), 50, update)
    cv2.createTrackbar('SNR (db)', win, int(opts.get('--snr', 25)), 50, update)
    update(None)

    while True:
        ch = cv2.waitKey() & 0xFF
        if ch == 27:                # press ESC key to exit
            cv2.destroyAllWindows()
            break
        if ch == ord('q'):
            defocus = not defocus
            update(None)
            cv2.destroyAllWindows()
