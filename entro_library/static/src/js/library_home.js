/** @odoo-module **/

import { Component, useState, onWillStart, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class LibraryHome extends Component {
    static template = "entro_library.LibraryHomeTemplate";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            resources: [],
            selectedResource: null,
            books: [],
            searchQuery: "",
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadResources();
            if (this.state.resources.length > 0) {
                await this.selectResource(this.state.resources[0]);
            }
            this.state.isLoading = false;
        });
    }

    async loadResources() {
        this.state.resources = await this.orm.searchRead(
            "library.resource",
            [["active", "=", true]],
            ["id", "name", "code", "policy", "description", "icon", "color", "book_count", "available_book_count", "borrowed_book_count"],
            { order: "sequence, name" }
        );
    }

    async selectResource(resource) {
        this.state.selectedResource = {
            ...resource,
            policy: resource.policy ? markup(resource.policy) : false,
            description: resource.description ? markup(resource.description) : false,
        };
        this.state.searchQuery = "";
        await this.loadBooks();
    }

    async loadBooks() {
        if (!this.state.selectedResource) {
            this.state.books = [];
            return;
        }

        let domain = [["resource_ids", "in", [this.state.selectedResource.id]]];

        if (this.state.searchQuery) {
            domain = [
                "&",
                ["resource_ids", "in", [this.state.selectedResource.id]],
                "|",
                "|",
                ["name", "ilike", this.state.searchQuery],
                ["author_ids.name", "ilike", this.state.searchQuery],
                ["keywords", "ilike", this.state.searchQuery],
            ];
        }

        this.state.books = await this.orm.searchRead(
            "library.book",
            domain,
            [
                "id",
                "name",
                "author_ids",
                "publisher_id",
                "publication_year",
                "category_id",
                "available_quant_count",
                "borrowed_quant_count",
                "quant_count",
                "image_1920",
            ],
            { limit: 50 }
        );
    }

    async onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        await this.loadBooks();
    }

    onBookClick(bookId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "library.book",
            res_id: bookId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    getBookImageUrl(book) {
        if (book.image_1920) {
            return `data:image/png;base64,${book.image_1920}`;
        }
        return "/web/static/img/placeholder.png";
    }

    getResourceIcon(resource) {
        return resource.icon || "fa-book";
    }

    getResourceLogo(resource, isActive = false) {
        // Return white logo if active, otherwise normal logo
        if (isActive) {
            return "/entro_library/static/src/image/white_logo.png";
        }
        return "/entro_library/static/src/image/logo.png";
    }
}

registry.category("actions").add("library_home", LibraryHome);
