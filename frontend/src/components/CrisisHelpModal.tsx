import { useState } from "react";
import { Modal, Button } from "react-bootstrap";

export function CrisisHelpButton() {
  const [show, setShow] = useState(false);

  return (
    <>
      <Button 
        variant="danger" 
        className="fw-bold d-flex align-items-center gap-2 rounded-pill px-4"
        onClick={() => setShow(true)}
      >
        <i className="bi bi-telephone-fill"></i> Get Help Now
      </Button>

      <Modal show={show} onHide={() => setShow(false)} centered size="lg">
        <Modal.Header closeButton className="bg-danger text-white border-0">
          <Modal.Title><i className="bi bi-exclamation-triangle-fill me-2"></i> Emergency Crisis Support</Modal.Title>
        </Modal.Header>
        <Modal.Body className="p-4">
          <div className="alert alert-danger border-0 rounded-3 mb-4">
            <h5 className="alert-heading fw-bold mb-2">If you or someone else is in immediate physical danger, call emergency services immediately!</h5>
            <p className="mb-0 fw-bold fs-4">Police / Ambulance: 999 or 112</p>
          </div>

          <div className="row g-4">
            <div className="col-md-6">
              <div className="card h-100 border-danger border-opacity-25 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title text-danger fw-bold"><i className="bi bi-heart-pulse-fill me-2"></i> Suicide Prevention</h5>
                  <p className="card-text text-muted mb-2">Befrienders Kenya (Toll Free)</p>
                  <a href="tel:+254722280264" className="btn btn-outline-danger w-100 fw-bold fs-5">+254 722 280 264</a>
                </div>
              </div>
            </div>
            
            <div className="col-md-6">
              <div className="card h-100 border-danger border-opacity-25 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title text-danger fw-bold"><i className="bi bi-telephone-plus-fill me-2"></i> Mental Health Support</h5>
                  <p className="card-text text-muted mb-2">Kenya Red Cross Toll Free</p>
                  <a href="tel:1199" className="btn btn-outline-danger w-100 fw-bold fs-5">1199</a>
                </div>
              </div>
            </div>

            <div className="col-md-6">
              <div className="card h-100 border-danger border-opacity-25 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title text-danger fw-bold"><i className="bi bi-shield-lock-fill me-2"></i> Gender-Based Violence</h5>
                  <p className="card-text text-muted mb-2">National Toll Free Helpline</p>
                  <a href="tel:1195" className="btn btn-outline-danger w-100 fw-bold fs-5">1195</a>
                </div>
              </div>
            </div>
            
            <div className="col-md-6">
              <div className="card h-100 border-danger border-opacity-25 shadow-sm">
                <div className="card-body">
                  <h5 className="card-title text-danger fw-bold"><i className="bi bi-hospital-fill me-2"></i> Facility Duty Clinician</h5>
                  <p className="card-text text-muted mb-2">On-Call Medical Officer</p>
                  <a href="tel:+254700000000" className="btn btn-outline-danger w-100 fw-bold fs-5">Call Duty Desk</a>
                </div>
              </div>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0">
          <Button variant="secondary" onClick={() => setShow(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
