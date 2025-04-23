// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertificateVerification {
    struct Certificate {
        string certificateHash;
        string metadataIpfsHash;
        uint256 timestamp;
        address issuer;
        bool isRevoked;
    }
    
    // Mapping from certificate ID to Certificate struct
    mapping(string => Certificate) public certificates;
    
    // Mapping to track authorized issuers
    mapping(address => bool) public authorizedIssuers;
    
    // Owner of the contract
    address public owner;
    
    // Events
    event CertificateIssued(string certificateId, string certificateHash, string metadataIpfsHash, address issuer);
    event CertificateRevoked(string certificateId, address revoker);
    event IssuerAuthorized(address issuer);
    event IssuerRevoked(address issuer);
    
    constructor() {
        owner = msg.sender;
        authorizedIssuers[msg.sender] = true;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorizedIssuer() {
        require(authorizedIssuers[msg.sender], "Not authorized to issue certificates");
        _;
    }
    
    function authorizeIssuer(address issuer) public onlyOwner {
        authorizedIssuers[issuer] = true;
        emit IssuerAuthorized(issuer);
    }
    
    function revokeIssuer(address issuer) public onlyOwner {
        require(issuer != owner, "Cannot revoke owner's issuer status");
        authorizedIssuers[issuer] = false;
        emit IssuerRevoked(issuer);
    }
    
    function issueCertificate(
        string memory certificateId, 
        string memory certificateHash, 
        string memory metadataIpfsHash
    ) public onlyAuthorizedIssuer {
        require(bytes(certificates[certificateId].certificateHash).length == 0, "Certificate ID already exists");
        
        certificates[certificateId] = Certificate({
            certificateHash: certificateHash,
            metadataIpfsHash: metadataIpfsHash,
            timestamp: block.timestamp,
            issuer: msg.sender,
            isRevoked: false
        });
        
        emit CertificateIssued(certificateId, certificateHash, metadataIpfsHash, msg.sender);
    }
    
    function revokeCertificate(string memory certificateId) public {
        Certificate storage cert = certificates[certificateId];
        require(bytes(cert.certificateHash).length > 0, "Certificate does not exist");
        require(cert.issuer == msg.sender || msg.sender == owner, "Not authorized to revoke this certificate");
        require(!cert.isRevoked, "Certificate already revoked");
        
        cert.isRevoked = true;
        emit CertificateRevoked(certificateId, msg.sender);
    }
    
    function verifyCertificate(string memory certificateId) public view returns (
        string memory certificateHash,
        string memory metadataIpfsHash,
        uint256 timestamp,
        address issuer,
        bool isRevoked
    ) {
        Certificate memory cert = certificates[certificateId];
        require(bytes(cert.certificateHash).length > 0, "Certificate does not exist");
        
        return (
            cert.certificateHash,
            cert.metadataIpfsHash,
            cert.timestamp,
            cert.issuer,
            cert.isRevoked
        );
    }
    
    function validateHash(string memory certificateId, string memory hashToValidate) public view returns (bool) {
        Certificate memory cert = certificates[certificateId];
        require(bytes(cert.certificateHash).length > 0, "Certificate does not exist");
        require(!cert.isRevoked, "Certificate has been revoked");
        
        return keccak256(abi.encodePacked(hashToValidate)) == keccak256(abi.encodePacked(cert.certificateHash));
    }
}
