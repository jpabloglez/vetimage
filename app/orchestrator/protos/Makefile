.PHONY: proto clean help

# Compile protocol buffer files
proto:
	@echo "Compiling protocol buffer files..."
	python -m grpc_tools.protoc \
		-I. \
		--python_out=../src \
		--grpc_python_out=../src \
		orchestrator.proto model_service.proto
	@echo "Proto files compiled successfully!"

# Clean generated files
clean:
	@echo "Cleaning generated proto files..."
	rm -f ../src/*_pb2.py
	rm -f ../src/*_pb2_grpc.py
	@echo "Clean complete!"

# Help target
help:
	@echo "Available targets:"
	@echo "  proto  - Compile protocol buffer files"
	@echo "  clean  - Remove generated proto files"
	@echo "  help   - Show this help message"
