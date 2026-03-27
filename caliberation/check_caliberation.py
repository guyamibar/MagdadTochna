import cv2
import numpy as np

# === YOUR CALIBRATION RESULTS ===
K = np.array([
    [1553.12643,    0.      , 930.736239],
    [   0.      , 1539.41589, 573.769916],
    [   0.      ,    0.      ,   1.      ]
], dtype=np.float64)

D = np.array([
    [  0.24397915],
    [  1.73456832],
    [-13.27475683],
    [ 38.16459386]
], dtype=np.float64)


def undistort_fisheye(img):
    h, w = img.shape[:2]

    # You can play with "balance" (0 = more crop, 1 = keep FOV)
    balance = 0.0
    dim = (w, h)


    newK = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
        K, D, dim, np.eye(3), balance=balance
    )

    map1, map2 = cv2.fisheye.initUndistortRectifyMap(
        K, D, np.eye(3), newK, dim, cv2.CV_16SC2
    )

    undistorted = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR)
    return undistorted


if __name__ == "__main__":
    img = cv2.imread("im0.jpg")  # put one of your images here
    und = undistort_fisheye(img)

    cv2.imshow("raw", img)
    cv2.imshow("undistorted", und)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    cv2.imwrite("raw_table_debug.jpg", img)
    cv2.imwrite("undistorted_debug.jpg", und)
