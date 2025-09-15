import { Modal } from 'react-bootstrap';
import React from 'react';

const ErrorModal = ({ show, message, onHide }) => {
  return (
    <Modal show={show} onHide={onHide}>
      <Modal.Header closeButton>
        <Modal.Title>错误提示</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="alert alert-danger">
          {message}
        </div>
      </Modal.Body>
    </Modal>
  );
};

export default ErrorModal;
