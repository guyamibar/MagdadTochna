import cv2
import numpy as np
import glob
#=== CALIBRATION COMPLETE ===
#K =
# [[7.49738901e+03 0.00000000e+00 9.65431572e+02]
# [0.00000000e+00 7.38982433e+03 5.14045919e+02]
# [0.00000000e+00 0.00000000e+00 1.00000000e+00]]
#D =
# [[-3.53729050e+00  7.87898961e+01  6.58652638e-03 -1.01447862e-01
#   8.53129260e-01]]
# Checkerboard spec (9x6 INNER corners)
CHECKERBOARD = (10, 7)
SQUARE_SIZE = 0.025  # 25mm per square (0.025 meters)

criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare 3D coordinates of the checkerboard corners
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

objpoints = []  # 3D points
imgpoints = []  # 2D corners

images = glob.glob('calib_images/*.jpg')
print("Found images:", len(images))

for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)

    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

        cv2.drawChessboardCorners(img, CHECKERBOARD, corners2, ret)
        cv2.imshow('Corners', img)
        cv2.waitKey(150)

cv2.destroyAllWindows()

# Calibrate
ret, K, D, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

print("\n\n=== CALIBRATION COMPLETE ===")
print("K =\n", K)
print("D =\n", D)
