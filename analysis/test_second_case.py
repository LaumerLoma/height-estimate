"""Physical recovery tests for the second case, independent of the real-image fit."""
import json
import unittest
import numpy as np
from analyze_second_case import motion_ratio, solve, Ground, DATA, PIN_G, PIN_S

class SecondCaseTests(unittest.TestCase):
    def test_shape_recovers_a_known_scan_motion(self):
        r=.92;ratio=np.array([-.6,.6]);B=np.array([[1-ratio[0],0],[-ratio[1],r]])
        body=np.linalg.solve(B,[20,-20]);wing=np.linalg.solve(B,[25,25])
        landmarks=np.array([body,[0,0],wing/2,-wing/2])
        np.testing.assert_allclose(motion_ratio(r,landmarks),ratio,atol=1e-12)

    def test_full_geometry_recovers_known_height_without_using_shadow_to_fit_motion(self):
        ground=lambda p:400.0
        height=200.;zc=3000.;Z=400+height;r=(zc-Z)/(zc-400)
        g=np.array([0.,-400.]);ratio=np.array([-.6,.6]);alpha=35.;az=158.
        u=np.array([np.sin(np.radians(az+180)),np.cos(np.radians(az+180))])
        L=height/np.tan(np.radians(alpha));de=L*u[0]/(1-ratio[0])
        shadow=g+np.array([de,L*u[1]+ratio[1]*de])
        image=np.array([g[0],g[1]/r])
        B=np.array([[1-ratio[0],0],[-ratio[1],r]])
        body=np.linalg.solve(B,[20.,-20.]);wing=np.linalg.solve(B,[25.,25.])
        p=dict(aircraft=image,shadow=shadow,zc=zc,x0=0.,elevation=alpha,azimuth=az,
               landmarks=np.array([body,[0,0],wing/2,-wing/2]))
        result=solve(p,ground)
        self.assertAlmostEqual(result['height_m'],height,places=8)
        self.assertAlmostEqual(result['cross_ray_residual_m'],0.,places=8)
        np.testing.assert_allclose(result['true_position'],g,atol=1e-8)

    def test_same_strip_footprint_contains_both_user_pins(self):
        ring=json.loads((DATA/'strip.json').read_text())['feature']['geometry']['rings'][0]
        def inside(p):
            e,n=p;hit=False
            for (e1,n1),(e2,n2) in zip(ring,ring[1:]+ring[:1]):
                if (n1>n)!=(n2>n) and e<(e2-e1)*(n-n1)/(n2-n1)+e1:hit=not hit
            return hit
        self.assertTrue(inside(PIN_G));self.assertTrue(inside(PIN_S))

    def test_terrain_is_not_silently_extrapolated(self):
        with self.assertRaises(ValueError):Ground()([0,0])

if __name__=='__main__':unittest.main()
