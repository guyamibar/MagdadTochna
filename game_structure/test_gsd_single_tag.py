import cv2
import numpy as np
import pytest
from game_structure.gsd import Gsd, TABLE_WIDTH, TABLE_HEIGHT

K = [
    [1.39561099e03, 0.00000000e00, 8.85690305e02],
    [0.00000000e00, 1.38830766e03, 5.04754597e02],
    [0.00000000e00, 0.00000000e00, 1.00000000e00],
]
camera_params = [K[0][0], K[1][1], K[0][2], K[1][2]]

@pytest.fixture
def gsd():
    return Gsd(camera_params)

def test_warp_table_exact_single_tag(gsd):
    image_paths = [
        "data/test tables/img3.png",
        "data/test tables/img4.png",
        "data/test tables/img5.png",
    ]

    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            pytest.fail(f"Could not read {path}")
        
        warped = gsd.warp_table_exact(img)
        cv2.imwrite(f"data/test_outputs/warped_table_{path[-8:-4]}.jpg", warped)

        assert warped is not None
        assert warped.shape == (TABLE_HEIGHT, TABLE_WIDTH, 3)
        
def test_get_table_homography_single_tag_behavior(gsd, monkeypatch):
    from game_structure.detecting_functions import read_apriltags
    from game_structure.models import AprilTagDetectionResult
    from game_structure.apriltag import AprilTag
    
    # Mock read_apriltags to return 1 tag
    mock_tag = AprilTag(tag_id=0, corners=[(100, 100), (200, 100), (200, 200), (100, 200)], center=(150, 150))
    
    def mock_read(frame, params):
        return AprilTagDetectionResult(annotated_image=frame, tags=[mock_tag])
    
    monkeypatch.setattr("game_structure.gsd.read_apriltags", mock_read)
    
    img = np.zeros((1000, 1200, 3), dtype=np.uint8)  # Sample image size
    # This calls get_table_homography
    homography = gsd.get_table_homography(img)
    
    assert homography is not None
    assert homography.shape == (3, 3)
    
    # Check that the homography maps mock corners to a SQUARE at the BOTTOM LEFT
    src_pts = np.float32([(100, 100), (200, 100), (200, 200), (100, 200)]).reshape(-1, 1, 2)
    dst_pts = cv2.perspectiveTransform(src_pts, homography)
    
    # Expected dst_pts for S=200 at bottom-left (0, 1800):
    # TL: (0, 1800-1-200=1599), TR: (200, 1599), BR: (200, 1799), BL: (0, 1799)
    expected_dst = np.float32([
        [0, 1599],
        [200, 1599],
        [200, 1799],
        [0, 1799]
    ]).reshape(-1, 1, 2)
    
    np.testing.assert_allclose(dst_pts, expected_dst, atol=1e-2)

def test_warp_table_exact_multiple_tags(gsd):
    path = "game_structure/data/test tables/img1.png"
    img = cv2.imread(path)
    if img is None:
        path = "game_structure/data/test tables/img1.jpg"
        img = cv2.imread(path)
        
    if img is not None:
        warped = gsd.warp_table_exact(img)
        assert warped is not None
        assert warped.shape == (TABLE_HEIGHT, TABLE_WIDTH, 3)
