import cv2
import numpy as np
import glob

images = glob.glob('caliberation/calib_images/*.jpg')
print("Found images:", len(images))

CHECKERBOARD = (7, 9)   # inner corners (from your board)
SQUARE_SIZE = 20.0      # mm

criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# base 3D pattern (N,3)
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float64)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2) * SQUARE_SIZE

objpoints = []  # will hold (1, N, 3) arrays, float64
imgpoints = []  # will hold (1, N, 2) arrays, float64

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    print(fname, "ret =", ret)

    if ret:
        # refine corners
        corners2 = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)

        # reshape to (1, N, 3) and (1, N, 2) and convert to float64
        objpoints.append(objp.reshape(1, -1, 3).astype(np.float64))
        imgpoints.append(corners2.reshape(1, -1, 2).astype(np.float64))

        vis = img.copy()
        cv2.drawChessboardCorners(vis, CHECKERBOARD, corners2, ret)
        cv2.imshow("corners", vis)
        cv2.waitKey(100)

cv2.destroyAllWindows()

if len(objpoints) == 0:
    raise RuntimeError("No corners detected! Check images.")

gray = cv2.cvtColor(cv2.imread(images[0]), cv2.COLOR_BGR2GRAY)
h, w = gray.shape[:2]

K = np.eye(3, dtype=np.float64)
D = np.zeros((4, 1), dtype=np.float64)

rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
    objectPoints=objpoints,
    imagePoints=imgpoints,
    image_size=(w, h),
    K=K,
    D=D,
    rvecs=None,
    tvecs=None,
    flags=cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC +
          cv2.fisheye.CALIB_CHECK_COND +
          cv2.fisheye.CALIB_FIX_SKEW,
    criteria=criteria
)

print("\n=== Calibration result ===")
print("RMS reprojection error:", rms)
print("K =\n", K)
print("D =\n", D)
